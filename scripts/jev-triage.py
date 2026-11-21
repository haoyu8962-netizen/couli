#!/usr/bin/env python3
"""Triage pending planning decisions with TypeSafe Jev (规划/11 §7.1, §7.3 第 13 项).

Requires Python >= 3.9, with no third-party dependencies.
  python3 scripts/kanban.py --json > board.json
  python3 scripts/jev-triage.py board.json out.json
  python3 scripts/jev-triage.py board.json out.json --dry-run    write the requests, call nothing

The key is read from the environment variable TYPESAFE_API_KEY only; never put it in a file.

Every open decision that waits on the owner gets one request with all questions merged, and
lands in one of three routes:
  risk_or_manual  one of the kinds 规划/11 §7.1 keeps with their original owner: spending
                  and new vendors, irreversible or outward actions, things the owner must do
                  in person, gates and rules, professional confirmation, material only the
                  owner has, results of a capability test. Jev does not decide these.
  review          Jev may decide, but the agent checks the premise first: money or
                  attribution, account or outward risk, no executable default, or an
                  uncertain answer. Review happens on the agent side, not with the owner.
  auto            none of the above: an executable default exists and nothing is at stake.
The route only sorts the items. Picking between options is a separate choice question, and
the write-back still lists what was chosen and Jev's confidence.

Exit status: 0 all answered, 1 some requests failed (the others are still written), 2 usage,
configuration or board-format problem.
"""

import argparse
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
import hashlib
import http.client
import json
import os
from pathlib import Path
import random
import re
import secrets
import sys
import tempfile
import threading
import time
import urllib.error
import urllib.request


ENDPOINT = "https://api.typesafe.ai/v1/systemone"
# A versioned id, not an alias: jev-latest moves when a release ships, and answers move with it.
MODEL = "jev-1.14.0"
# Input tokens only, output is free (docs.typesafe.ai/models, read 2026-11-21).
PRICE_USD_PER_MTOK = 0.042
# Starting values, not tuned on labelled items; the raw probabilities are kept in the output.
YES, NO = 0.7, 0.3
TIMEOUT_S = 30
MAX_ATTEMPTS = 4
BACKOFF_INITIAL_S, BACKOFF_MAX_S, RETRY_AFTER_MAX_S = 0.5, 8.0, 30.0
RETRY_STATUSES = {408, 429} | set(range(500, 600))   # 529 = overloaded
ACTIVE = ("open", "in_progress", "blocked")
FIELD_CHARS = 1500
ITEM_TEXT_KEYS = ("id", "title", "kind", "status", "status_raw", "owner", "group")   # plus the list `fields`
SERVER_ID_HEADERS = ("x-request-id", "request-id", "x-trace-id", "traceparent", "cf-ray")
# 规划/11 §7.1：原决策人是这几方的专业确认不交给 Jev。
PROFESSIONS = ("法务", "财务", "税务", "运营", "契约线")
# What happens while nobody decides, most explicit header first. A bare 建议 column is a
# recommendation, not a default, and is left out on purpose.
DEFAULT_HEADERS = ("默认", "现在怎么处理")


def noul(instructions, yes=None, no=None):
    question = {"type": "noul", "instructions": instructions}
    if yes is not None:
        question["criteria"] = {"true": yes, "false": no}
    return question


# 规划/11 §7.1：这几类不交给 Jev，仍按原责任处理。
MANUAL = {
    "spend_or_vendor": noul(
        "落实这条待确认事项，是否需要付费，或新增供应商、模型、第三方 SDK？",
        "要花钱（采购、开通付费服务、追加预算），或要引入新的供应商、模型、第三方 SDK",
        "不花钱，也不引入新的供应商、模型或第三方 SDK"),
    "external_or_irreversible": noul(
        "定下这条待确认事项本身，是否就等于要去执行一个不可逆或对外的动作？",
        "定下来就要去做生产部署、真实下单或打款、调账、数据订正、提审、给真实用户发消息、公开发布这类动作",
        "只是选定取值、口径、规则或文案，或写成配置、开关，随时可以改回；规则讲的是打款、调账、发消息，"
        "而真正执行要以后按规则另行进行的，也算这一类"),
    "owner_in_person": noul(
        "这条待确认事项是否必须由负责人本人操作才能完成？",
        "要负责人本人登录、收验证码、实名、签名、同意协议、付款或运行带密钥的命令",
        "代理按文档就能落实，不需要负责人本人操作"),
    "gate_or_rule": noul(
        "这条待确认事项是否是在改门禁或协作规则本身？",
        "要改保护路径里的文件、给检查开豁免（waived）、放宽密钥扫描、删除或放宽测试、改钩子或权限设置，"
        "或确认一条平台能力（CAP）的结论",
        "是产品做法、取值或文案的选择，不改门禁、检查、钩子或权限"),
    "professional_confirm": noul(
        "这条待确认事项的文字（含原决策人 `decider`、状态 `status_note`）里，是否写明要等法务、财务、税务、运营或契约线给出意见、答复或结论？",
        "文字里明确写了要等这些专业方的意见、答复、确认或结论，例如「待法务意见」「由财务确认」「税务结论」",
        "文字里没有写要等专业方；事项只是涉及金额、资金口径、奖励、风控或合规话题的，不算"),
    "owner_material": noul(
        "这条待确认事项缺的是否是只有负责人能提供的资料或内容？",
        "缺的是名称、域名、账号、资质材料、文案原稿这类要负责人提供的东西",
        "资料已经齐，只是要在已有做法里确认或选择"),
    "capability_test": noul(
        "这条待确认事项的结论，是否取决于还没做的平台能力实测？状态 `status_note` 里写了待实测的也算。",
        "要等接口实际返回、限额、审核结果这类实测出来才能定",
        "不依赖实测，现在就能按文档定"),
}
# 命中时仍由 Jev 判断，但代理先核实题干、补影响说明并复核，再回写；不回到负责人。
REVIEW = {
    "money_or_attr": noul(
        "这条待确认事项的决定，会不会改变用户拿到的钱、订单或邀请关系归到谁名下、平台的资金口径或资金安全控制？",
        "会影响金额、资金口径、资金操作的安全控制，或订单/邀请人的归属",
        "只影响界面文案、显示方式、远期功能约束或内部技术细节"),
    "account_or_risk": noul(
        "这条事项是否涉及用户账号安全与授权、个人信息处理、对外承诺，或可能招致平台封禁、监管、商店审核风险？"),
}
HAS_DEFAULT = "has_default"
QUESTIONS = {
    **MANUAL, **REVIEW,
    HAS_DEFAULT: noul("`default` 字段是否给出了一个明确可执行的默认做法（而不是写「未定」「没有默认」「不自拟」）？"),
}


class Problem(Exception):
    """Usage, configuration or board-format problem: nothing was sent."""


class CallError(Exception):
    def __init__(self, kind, status, detail, attempts):
        super().__init__(f"{kind} {status or ''} {detail}".strip())
        self.kind, self.status, self.detail, self.attempts = kind, status, detail, attempts

    def record(self):
        return {"kind": self.kind, "status": self.status, "detail": self.detail, "attempts": self.attempts}


class NoRedirect(urllib.request.HTTPRedirectHandler):
    """A redirect would carry the Authorization header to another host; refuse it."""

    def redirect_request(self, *args, **kwargs):
        return None


OPENER = urllib.request.build_opener(NoRedirect)


def scrub(text, key):
    """Error text is kept and printed, and a gateway or a library may echo the header back."""
    text = text.replace(key, "<key>") if key else text
    return re.sub(r"Bearer\s+\S+", "Bearer <redacted>", text)


def select(board):
    """Open decisions that wait on the owner, as the board counts them (kanban.py `owner_open`)."""
    items = board.get("open_items") if isinstance(board, dict) else None
    if not isinstance(items, list):
        raise Problem("看板 JSON 里没有 open_items 列表；请用 scripts/kanban.py --json 生成")
    for item in items:
        fields = item.get("fields") if isinstance(item, dict) else None
        sound = (isinstance(fields, list) and all(isinstance(item.get(key), str) for key in ITEM_TEXT_KEYS)
                 and all(isinstance(pair, list) and len(pair) == 2 and all(isinstance(part, str) for part in pair)
                         for pair in fields))
        if not sound:
            name = item.get("id", "?") if isinstance(item, dict) else "?"
            raise Problem(f"open_items 的条目 {name} 缺字段或类型不对（要有文字字段 {'、'.join(ITEM_TEXT_KEYS)} "
                          "和成对的 fields）：kanban.py 的输出变了，先对齐本脚本再跑")
    return [item for item in items
            if item["kind"] == "decision" and item["status"] in ACTIVE
            and not item.get("same_as") and item["owner"].startswith("负责人")]


def default_of(fields):
    """The column that states what happens if nobody decides; its header differs between tables."""
    for wanted in DEFAULT_HEADERS:
        for name, text in fields:
            if wanted in name and text.strip():
                return name, text
    return None, ""


def state_of(item):
    name, text = default_of(item["fields"])
    return name, {
        "item": item["title"], "listed_in": item["group"], "decider": item["owner"],
        # The board keeps the status column out of `fields`, and conditions are often written there.
        "status_note": item["status_raw"][:FIELD_CHARS],
        "default": text[:FIELD_CHARS],
        "fields": {field: value[:FIELD_CHARS] for field, value in item["fields"]},
    }


def retry_after_seconds(value):
    """Retry-After is either seconds or an HTTP date."""
    try:
        return float(value)
    except (TypeError, ValueError):
        pass
    try:
        return (parsedate_to_datetime(value) - datetime.now(timezone.utc)).total_seconds()
    except (TypeError, ValueError):
        return None


def backoff(attempt, retry_after):
    delay = min(BACKOFF_MAX_S, BACKOFF_INITIAL_S * 2 ** (attempt - 1)) * (1 + random.uniform(0, 0.25))
    asked = retry_after_seconds(retry_after)
    return delay if asked is None else max(delay, min(asked, RETRY_AFTER_MAX_S))


def count(value):
    return isinstance(value, int) and not isinstance(value, bool) and value >= 0


def checked(payload, model):
    """The documented response has no status field, so a 200 is checked by shape."""
    if not isinstance(payload, dict):
        raise ValueError("响应不是 JSON 对象")
    answered = payload.get("model")
    if not isinstance(answered, str) or not answered:
        raise ValueError("响应缺应答模型的版本号")
    if answered != model and not model.endswith(("-latest", "-preview")):
        raise ValueError(f"应答模型是 {answered!r}，请求的是 {model!r}")
    answers = payload.get("answers")
    if not isinstance(answers, dict):
        raise ValueError("响应缺 answers")
    probabilities = {}
    for key in QUESTIONS:
        answer = answers.get(key)
        value = answer.get("noul") if isinstance(answer, dict) and answer.get("type") == "noul" else None
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not 0 <= value <= 1:
            raise ValueError(f"问题 {key} 的应答不是 0–1 的概率：{json.dumps(answer, ensure_ascii=False)[:200]}")
        probabilities[key] = float(value)
    usage = payload.get("usage")
    if not isinstance(usage, dict) or not count(usage.get("input_tokens")) or not count(usage.get("output_tokens")):
        raise ValueError("响应的 usage 缺 input_tokens 或 output_tokens，或不是非负整数")
    return answered, probabilities, {"input_tokens": usage["input_tokens"], "output_tokens": usage["output_tokens"]}


def ask(key, model, state, sleep=time.sleep, halted=lambda: False):
    """One request with every question; retries overload and network failures, nothing else."""
    body = json.dumps({"model": model, "state": state, "questions": QUESTIONS}, ensure_ascii=False).encode("utf-8")
    headers = {"Authorization": "Bearer " + key, "Content-Type": "application/json"}
    began = time.perf_counter()
    for attempt in range(1, MAX_ATTEMPTS + 1):
        if halted():   # another request was refused for the key; a retry would be refused too
            raise CallError("skipped", None, "鉴权被拒后未发送", attempt - 1)
        last = attempt == MAX_ATTEMPTS
        started = time.perf_counter()
        try:
            with OPENER.open(urllib.request.Request(ENDPOINT, body, headers), timeout=TIMEOUT_S) as response:
                raw, seen = response.read(), response.headers
        except urllib.error.HTTPError as error:
            try:
                detail = scrub(error.read()[:600].decode("utf-8", "replace"), key)
            except (OSError, http.client.HTTPException):   # the status is known even if the body is not
                detail = ""
            if error.code in RETRY_STATUSES and not last:
                sleep(backoff(attempt, error.headers.get("Retry-After") if error.headers else None))
                continue
            raise CallError("http", error.code, detail, attempt) from None
        except (OSError, http.client.HTTPException) as error:   # timeouts, resets, DNS, truncated bodies
            if not last:
                sleep(backoff(attempt, None))
                continue
            raise CallError("network", None, scrub(str(getattr(error, "reason", None) or error), key), attempt) from None
        latency_ms = (time.perf_counter() - started) * 1000
        try:
            answered, probabilities, usage = checked(json.loads(raw), model)
        except ValueError as error:   # includes JSONDecodeError; the same request would fail the same way
            raise CallError("response", 200, scrub(str(error), key), attempt) from None
        return {
            "model": answered, "answers": probabilities, "usage": usage, "attempts": attempt,
            "latency_ms": round(latency_ms, 1), "elapsed_ms": round((time.perf_counter() - began) * 1000, 1),
            "server_ids": {name: seen[name] for name in SERVER_ID_HEADERS if seen.get(name)},
        }


def route(answers, has_default_text, decider=""):
    hits = [f"{key}={answers[key]:.2f}" for key in MANUAL if answers[key] >= YES]
    named = [word for word in PROFESSIONS if word in decider]
    if named:   # the board's own column says so; no judgment needed
        hits.append("decider=" + "、".join(named))
    if hits:
        return "risk_or_manual", hits
    reasons = [f"{key}={answers[key]:.2f}（不确定）" for key in MANUAL if answers[key] > NO]
    reasons += [f"{key}={answers[key]:.2f}" for key in REVIEW if answers[key] > NO]
    if not has_default_text:
        reasons.append("default_empty")
    elif answers[HAS_DEFAULT] < YES:
        reasons.append(f"{HAS_DEFAULT}={answers[HAS_DEFAULT]:.2f}")
    return ("review" if reasons else "auto"), reasons


def percentile(values, share):
    ordered = sorted(values)
    return ordered[max(0, -(-len(ordered) * share // 100) - 1)] if ordered else None


def triage(jobs, key, model, workers, ask=ask):
    """Each job is answered or recorded as a failure; one bad request does not lose the rest."""
    rejected = threading.Event()

    def work(job):
        head = {"id": job["item"]["id"], "title": job["item"]["title"], "request_id": job["request_id"]}
        try:
            reply = ask(key, model, job["state"], halted=rejected.is_set)
        except CallError as error:
            if error.status in (401, 403):
                rejected.set()
            return {**head, "error": error.record()}
        except Exception as error:   # a bug here must not discard the answers already in hand
            detail = scrub(f"{type(error).__name__}: {error}", key)
            return {**head, "error": {"kind": "internal", "status": None, "detail": detail, "attempts": 0}}
        chosen, reasons = route(reply["answers"], job["state"]["default"], job["state"]["decider"])
        return {**head, "listed_in": job["item"]["group"], "decider": job["item"]["owner"],
                "route": chosen, "reasons": reasons, "default_field": job["default_field"], **reply,
                "cost_usd": round(reply["usage"]["input_tokens"] * PRICE_USD_PER_MTOK / 1e6, 8)}

    with ThreadPoolExecutor(max(1, workers)) as pool:
        return list(pool.map(work, jobs))


def summary(results):
    done = [entry for entry in results if "error" not in entry]
    latencies = [entry["latency_ms"] for entry in done]
    tokens = sum(entry["usage"]["input_tokens"] for entry in done)
    return {
        "selected": len(results), "ok": len(done), "failed": len(results) - len(done),
        "routes": {name: sum(entry["route"] == name for entry in done) for name in ("auto", "review", "risk_or_manual")},
        "default_empty": sum(entry["default_field"] is None for entry in done),
        "retries": sum(entry["attempts"] - 1 for entry in done)
                   + sum(max(0, entry["error"]["attempts"] - 1) for entry in results if "error" in entry),
        "input_tokens": tokens, "output_tokens": sum(entry["usage"]["output_tokens"] for entry in done),
        "cost_usd": round(tokens * PRICE_USD_PER_MTOK / 1e6, 6),
        "latency_ms": {"p50": percentile(latencies, 50), "p95": percentile(latencies, 95),
                       "max": max(latencies) if latencies else None},
    }


def save(path, data):
    """Readers see the old file or the new one; a draft of its own keeps two runs apart."""
    target = Path(path)
    draft = None
    try:
        handle, draft = tempfile.mkstemp(dir=target.resolve().parent, prefix=target.name + ".", suffix=".part")
        with os.fdopen(handle, "w", encoding="utf-8") as file:
            file.write(json.dumps(data, ensure_ascii=False, indent=1) + "\n")
        os.replace(draft, target)
    except OSError as error:
        if draft and os.path.exists(draft):
            os.unlink(draft)
        raise Problem(f"写不了 {target}：{error}") from None


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("board", help="scripts/kanban.py --json 的输出文件")
    parser.add_argument("out", help="结果写到哪个 JSON 文件（要长期留的放 couli-runs/JEV/）")
    parser.add_argument("--model", default=MODEL, metavar="版本", help=f"Jev 版本号（默认 {MODEL}）")
    parser.add_argument("--workers", type=int, default=4, metavar="个数", help="并发请求数（默认 4）")
    parser.add_argument("--limit", type=int, metavar="条数", help="只跑前几条，试跑用")
    parser.add_argument("--dry-run", action="store_true", help="只把要发的请求写进结果文件，不调用接口，也不需要 Key")
    args = parser.parse_args(argv)
    try:
        try:
            board = json.loads(Path(args.board).read_text(encoding="utf-8"))
        except (OSError, ValueError) as error:
            raise Problem(f"读不了看板 JSON {args.board}：{error}") from None
        folder = Path(args.out).resolve().parent
        if not folder.is_dir() or not os.access(folder, os.W_OK):   # found out before any request is paid for
            raise Problem(f"结果目录不存在或不可写：{folder}")
        items = select(board)[:args.limit]
        # A table the board could not read means decisions are missing here without a trace.
        warnings = [str(text) for text in board.get("warnings") or []]
        if warnings:
            print(f"注意：看板有 {len(warnings)} 条告警，入选条目可能不全：", file=sys.stderr)
            for text in warnings:
                print(f"  {text}", file=sys.stderr)
        run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + "-" + secrets.token_hex(3)
        jobs = []
        for index, item in enumerate(items, 1):
            name, state = state_of(item)
            jobs.append({"item": item, "state": state, "default_field": name, "request_id": f"{run_id}-{index:03d}"})
        source = (board.get("sources") or {}).get("planning") or {}
        run = {
            "run_id": run_id, "endpoint": ENDPOINT, "model_requested": args.model,
            "board": {"generated_at": board.get("generated_at"), "warnings": warnings,
                      **{key: source.get(key) for key in ("mode", "ref", "branch", "sha", "dirty")}},
            "thresholds": {"yes": YES, "no": NO}, "price_usd_per_mtok": PRICE_USD_PER_MTOK,
            "questions_sha256": hashlib.sha256(json.dumps(QUESTIONS, ensure_ascii=False, sort_keys=True).encode("utf-8")).hexdigest(),
            "questions": QUESTIONS,
        }
        empty = [job["item"]["id"] for job in jobs if job["default_field"] is None]
        if args.dry_run:
            save(args.out, {"run": {**run, "dry_run": True}, "requests": [
                {"id": job["item"]["id"], "request_id": job["request_id"], "default_field": job["default_field"],
                 "state": job["state"]} for job in jobs]})
            print(f"试排：入选 {len(jobs)} 条，没取到默认做法的 {len(empty)} 条{'：' + '、'.join(empty) if empty else ''}")
            print(f"请求内容已写入 {args.out}，没有调用接口")
            return 0
        key = os.environ.get("TYPESAFE_API_KEY", "").strip()   # a copied key often ends in a newline
        if not key:
            raise Problem("没有设置环境变量 TYPESAFE_API_KEY")
        if not key.isascii() or not key.isprintable() or " " in key:
            raise Problem("环境变量 TYPESAFE_API_KEY 中间有空白、换行或非 ASCII 字符，不像一把完整的 Key")
        if args.model.endswith(("-latest", "-preview")):
            print(f"注意：{args.model} 是别名，会随发布变动；记录以应答里的版本号为准", file=sys.stderr)
        results = triage(jobs, key, args.model, args.workers)
        stats = summary(results)
        done = [entry for entry in results if "error" not in entry]
        failures = [entry for entry in results if "error" in entry]
        run["models_answered"] = sorted({entry["model"] for entry in done})
        save(args.out, {"run": run, "stats": stats, "items": done, "failures": failures})
    except Problem as problem:
        print(f"jev-triage: {problem}", file=sys.stderr)
        return 2
    routes, latency = stats["routes"], stats["latency_ms"]
    print(f"模型 {'、'.join(run['models_answered']) or args.model}｜入选 {stats['selected']} 条，成功 {stats['ok']}，"
          f"失败 {stats['failed']}，重试 {stats['retries']} 次")
    print(f"分流：auto {routes['auto']}｜review {routes['review']}｜risk_or_manual {routes['risk_or_manual']}")
    if empty:
        print(f"没取到默认做法的 {len(empty)} 条（不会进 auto）：{'、'.join(empty)}")
    if done:
        print(f"输入 token {stats['input_tokens']}，费用约 ${stats['cost_usd']:.6f}；"
              f"单次耗时 P50 {latency['p50']:.0f} ms，P95 {latency['p95']:.0f} ms")
    for entry in failures:
        error = entry["error"]
        print(f"失败 {entry['id']}（{entry['request_id']}）：{error['kind']} {error['status'] or ''} {error['detail']}".rstrip(),
              file=sys.stderr)
    print(f"结果已写入 {args.out}")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
