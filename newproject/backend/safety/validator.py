import re
import base64
from typing import Dict, Any, List, Tuple
from dataclasses import dataclass
from enum import Enum

from backend.safety.rules import (
    DANGEROUS_COMMANDS,
    DANGEROUS_PARAMS,
    PROTECTED_PATHS,
    INJECTION_PATTERNS_EN,
    INJECTION_PATTERNS_CN,
    ALLOWED_COMMANDS,
    INTENT_KEYWORDS,
    PATH_WHITELIST,
    PATH_BLACKLIST,
    BLOCKED_PIDS,
    UNICODE_HOMOGLYPHS,
    ZERO_WIDTH_CHARS,
    CONTROL_CHAR_RANGES,
    RISK_SCORE_THRESHOLDS,
)


class RiskLevel(Enum):
    SAFE = "safe"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class RiskCheckResult:
    is_safe: bool
    risk_level: RiskLevel
    risk_reasons: List[str]
    suggested_fixes: List[str]


def _score_to_risk_level(score: float) -> RiskLevel:
    if score >= RISK_SCORE_THRESHOLDS["critical"]:
        return RiskLevel.CRITICAL
    if score >= RISK_SCORE_THRESHOLDS["high"]:
        return RiskLevel.HIGH
    if score >= RISK_SCORE_THRESHOLDS["medium"]:
        return RiskLevel.MEDIUM
    if score >= RISK_SCORE_THRESHOLDS["low"]:
        return RiskLevel.LOW
    return RiskLevel.SAFE


def _max_risk_level(levels: List[RiskLevel]) -> RiskLevel:
    priority = {
        RiskLevel.SAFE: 0,
        RiskLevel.LOW: 1,
        RiskLevel.MEDIUM: 2,
        RiskLevel.HIGH: 3,
        RiskLevel.CRITICAL: 4,
    }
    return max(levels, key=lambda lv: priority[lv])


class InputSanitizer:

    @staticmethod
    def _detect_homoglyphs(text: str) -> Tuple[str, List[str]]:
        warnings: List[str] = []
        cleaned = list(text)
        for i, char in enumerate(text):
            if char in UNICODE_HOMOGLYPHS:
                warnings.append(
                    f"位置 {i}: 检测到 Unicode 同形字 '{char}' "
                    f"-> 替换为拉丁字符 '{UNICODE_HOMOGLYPHS[char]}'"
                )
                cleaned[i] = UNICODE_HOMOGLYPHS[char]
        return "".join(cleaned), warnings

    @staticmethod
    def _detect_zero_width(text: str) -> Tuple[str, List[str]]:
        warnings: List[str] = []
        found_positions: List[int] = []
        for i, char in enumerate(text):
            if char in ZERO_WIDTH_CHARS:
                found_positions.append(i)
        if found_positions:
            warnings.append(
                f"检测到 {len(found_positions)} 个零宽字符，位置: {found_positions}"
            )
        cleaned = "".join(ch for ch in text if ch not in ZERO_WIDTH_CHARS)
        return cleaned, warnings

    @staticmethod
    def _remove_control_chars(text: str) -> Tuple[str, List[str]]:
        warnings: List[str] = []
        original_len = len(text)

        def _is_control(char: str) -> bool:
            cp = ord(char)
            return any(start <= cp <= end for start, end in CONTROL_CHAR_RANGES)

        cleaned = "".join(ch for ch in text if not _is_control(ch))
        removed_count = original_len - len(cleaned)
        if removed_count > 0:
            warnings.append(f"移除了 {removed_count} 个控制字符")
        return cleaned, warnings

    @staticmethod
    def sanitize(user_input: str) -> Tuple[str, List[str]]:
        all_warnings: List[str] = []

        text, hw = InputSanitizer._detect_homoglyphs(user_input)
        all_warnings.extend(hw)

        text, zw = InputSanitizer._detect_zero_width(text)
        all_warnings.extend(zw)

        text, cw = InputSanitizer._remove_control_chars(text)
        all_warnings.extend(cw)

        return text, all_warnings


class IntentClassifier:

    @staticmethod
    def classify_intent(user_input: str) -> Dict[str, Any]:
        scores: Dict[str, float] = {intent: 0.0 for intent in INTENT_KEYWORDS}
        matched_keywords: Dict[str, List[str]] = {intent: [] for intent in INTENT_KEYWORDS}

        input_lower = user_input.lower()

        for intent, keywords in INTENT_KEYWORDS.items():
            for keyword, weight in keywords.items():
                if keyword.lower() in input_lower:
                    scores[intent] += weight
                    matched_keywords[intent].append(keyword)

        max_score = max(scores.values()) if scores.values() else 0.0
        if max_score == 0.0:
            return {
                "intent": "unknown",
                "confidence": 0.0,
                "risk_level": RiskLevel.SAFE.value,
                "matched_keywords": {},
            }

        primary_intent = max(scores, key=lambda k: scores[k])
        total = sum(scores.values())
        confidence = scores[primary_intent] / total if total > 0 else 0.0

        intent_risk_map = {
            "query": RiskLevel.SAFE,
            "diagnose": RiskLevel.LOW,
            "modify": RiskLevel.MEDIUM,
            "dangerous": RiskLevel.HIGH,
        }

        return {
            "intent": primary_intent,
            "confidence": round(confidence, 3),
            "risk_level": intent_risk_map.get(primary_intent, RiskLevel.SAFE).value,
            "matched_keywords": {k: v for k, v in matched_keywords.items() if v},
        }


class RiskScorer:

    @staticmethod
    def score_risk(command: str) -> Dict[str, Any]:
        score = 0.0
        reasons: List[str] = []
        suggestions: List[str] = []
        matched_actions: List[str] = []

        for pattern, rule in DANGEROUS_COMMANDS.items():
            if re.search(pattern, command, re.IGNORECASE):
                score = max(score, rule["risk"])
                reasons.append(f"危险命令: {rule['description']} (模式: {pattern})")
                if rule["action"] == "block":
                    suggestions.append(f"此命令已被标记为禁止执行: {rule['description']}")
                elif rule["action"] == "confirm":
                    suggestions.append(f"此命令需要二次确认: {rule['description']}")
                else:
                    suggestions.append(f"建议谨慎操作: {rule['description']}")
                matched_actions.append(rule["action"])

        for param_pattern, risk_addition in DANGEROUS_PARAMS.items():
            if re.search(r"(?<![a-zA-Z])" + re.escape(param_pattern) + r"(?![a-zA-Z])", command):
                score = min(1.0, score + risk_addition)
                reasons.append(f"检测到高风险参数: {param_pattern}")

        for path_pattern in PROTECTED_PATHS:
            if re.search(path_pattern, command):
                score = min(1.0, score + 0.2)
                reasons.append(f"操作涉及受保护路径: {path_pattern}")
                suggestions.append("需要管理员权限二次审批")

        level = _score_to_risk_level(score)

        return {
            "score": round(score, 2),
            "level": level.value,
            "reasons": reasons,
            "suggestions": suggestions,
            "actions": matched_actions,
        }


class ParameterValidator:

    @staticmethod
    def _extract_paths(command: str) -> List[str]:
        tokens = command.split()
        paths: List[str] = []
        for i, token in enumerate(tokens):
            if i > 0 and tokens[i - 1].startswith("-"):
                continue
            if "/" in token or token.startswith("."):
                cleaned = token.strip("'\"`")
                paths.append(cleaned)
        return paths

    @staticmethod
    def _extract_pids(command: str) -> List[int]:
        pids: List[int] = []
        pid_patterns = [
            r"kill\s+(-\d+\s+)?(\d+)",
            r"killall\s+",
            r"-p\s+(\d+)",
            r"--pid[= ](\d+)",
            r"\bpid[= ](\d+)",
        ]
        for pattern in pid_patterns:
            for match in re.finditer(pattern, command):
                for group in match.groups():
                    if group and group.isdigit():
                        pids.append(int(group))
        return pids

    @staticmethod
    def validate_params(command: str, params: Dict[str, Any] = None) -> Dict[str, Any]:
        violations: List[str] = []
        paths = ParameterValidator._extract_paths(command)

        for path in paths:
            is_whitelisted = any(re.match(wp, path) for wp in PATH_WHITELIST)
            is_blacklisted = any(re.match(bp, path) for bp in PATH_BLACKLIST)

            if is_blacklisted:
                violations.append(f"路径在黑名单中: {path}")
            elif not is_whitelisted and "/" in path and path != "." and path != "..":
                violations.append(f"路径不在白名单中: {path} (允许: /tmp, /var/log, /home, /opt)")

        pids = ParameterValidator._extract_pids(command)
        for pid in pids:
            if pid in BLOCKED_PIDS or pid < 1:
                violations.append(f"PID 不允许: {pid} (禁止: PID 0, 1, 2 及负数)")

        if params:
            for key, value in params.items():
                if isinstance(value, str) and "/" in value:
                    is_whitelisted = any(re.match(wp, value) for wp in PATH_WHITELIST)
                    is_blacklisted = any(re.match(bp, value) for bp in PATH_BLACKLIST)
                    if is_blacklisted:
                        violations.append(f"参数 {key} 的路径在黑名单中: {value}")
                    elif not is_whitelisted and value.startswith("/"):
                        violations.append(f"参数 {key} 的路径不在白名单中: {value}")

        return {
            "valid": len(violations) == 0,
            "violations": violations,
        }


class InjectionDetector:

    @staticmethod
    def _detect_base64(text: str) -> List[str]:
        findings: List[str] = []
        base64_pattern = r"[A-Za-z0-9+/]{20,}={0,2}"
        for match in re.finditer(base64_pattern, text):
            candidate = match.group()
            try:
                decoded = base64.b64decode(candidate).decode("utf-8", errors="ignore")
                if any(
                    cmd in decoded.lower()
                    for cmd in ["rm ", "kill", "chmod", "wget", "curl", "eval", "exec", "bash", "sh "]
                ):
                    findings.append(f"Base64 编码的危险命令: {candidate[:30]}... -> {decoded[:50]}")
            except Exception:
                pass
        return findings

    @staticmethod
    def _detect_hex(text: str) -> List[str]:
        findings: List[str] = []
        hex_pattern = r"(?:\\x[0-9a-fA-F]{2}){5,}"
        for match in re.finditer(hex_pattern, text):
            candidate = match.group()
            try:
                parts = re.findall(r"\\x([0-9a-fA-F]{2})", candidate)
                decoded = bytes(int(p, 16) for p in parts).decode("utf-8", errors="ignore")
                if any(
                    cmd in decoded.lower()
                    for cmd in ["rm ", "kill", "chmod", "wget", "curl", "eval", "exec", "bash", "sh "]
                ):
                    findings.append(f"Hex 编码的危险命令: {candidate} -> {decoded[:50]}")
            except Exception:
                pass
        return findings

    @staticmethod
    def detect_injection(user_input: str) -> Dict[str, Any]:
        patterns_found: List[str] = []

        for pattern in INJECTION_PATTERNS_EN:
            if re.search(pattern, user_input, re.IGNORECASE):
                patterns_found.append(f"[EN] {pattern}")

        for pattern in INJECTION_PATTERNS_CN:
            if re.search(pattern, user_input):
                patterns_found.append(f"[CN] {pattern}")

        b64_findings = InjectionDetector._detect_base64(user_input)
        patterns_found.extend(b64_findings)

        hex_findings = InjectionDetector._detect_hex(user_input)
        patterns_found.extend(hex_findings)

        detected = len(patterns_found) > 0
        if not detected:
            risk_level = RiskLevel.SAFE.value
        elif len(patterns_found) >= 3:
            risk_level = RiskLevel.CRITICAL.value
        elif len(patterns_found) >= 2:
            risk_level = RiskLevel.HIGH.value
        else:
            risk_level = RiskLevel.MEDIUM.value

        return {
            "detected": detected,
            "patterns_found": patterns_found,
            "risk_level": risk_level,
        }


class SafetyGuardrail:

    def __init__(self):
        self._sanitizer = InputSanitizer()
        self._intent_classifier = IntentClassifier()
        self._risk_scorer = RiskScorer()
        self._param_validator = ParameterValidator()
        self._injection_detector = InjectionDetector()

    def validate(self, user_input: str, generated_command: str = None) -> Dict[str, Any]:
        sanitized_input, sanitizer_warnings = self._sanitizer.sanitize(user_input)

        intent_result = self._intent_classifier.classify_intent(sanitized_input)

        injection_result = self._injection_detector.detect_injection(sanitized_input)

        risk_result = None
        param_result = None
        if generated_command:
            risk_result = self._risk_scorer.score_risk(generated_command)
            param_result = self._param_validator.validate_params(generated_command)

        layer_results = {
            "sanitizer": {
                "passed": len(sanitizer_warnings) == 0,
                "risk_level": RiskLevel.LOW.value if sanitizer_warnings else RiskLevel.SAFE.value,
                "warnings": sanitizer_warnings,
                "cleaned_input": sanitized_input,
            },
            "intent": {
                "passed": intent_result["intent"] != "dangerous",
                "risk_level": intent_result["risk_level"],
                "intent": intent_result["intent"],
                "confidence": intent_result["confidence"],
                "matched_keywords": intent_result["matched_keywords"],
            },
            "injection": {
                "passed": not injection_result["detected"],
                "risk_level": injection_result["risk_level"],
                "patterns_found": injection_result["patterns_found"],
            },
        }

        if risk_result:
            layer_results["risk_scorer"] = {
                "passed": risk_result["level"] not in ("high", "critical"),
                "risk_level": risk_result["level"],
                "score": risk_result["score"],
                "reasons": risk_result["reasons"],
                "suggestions": risk_result["suggestions"],
            }

        if param_result:
            layer_results["param_validator"] = {
                "passed": param_result["valid"],
                "risk_level": RiskLevel.HIGH.value if not param_result["valid"] else RiskLevel.SAFE.value,
                "violations": param_result["violations"],
            }

        all_risk_levels = [
            RiskLevel(layer["risk_level"]) for layer in layer_results.values()
        ]
        overall_risk = _max_risk_level(all_risk_levels)
        is_safe = all(layer["passed"] for layer in layer_results.values())

        return {
            "is_safe": is_safe,
            "overall_risk": overall_risk.value,
            "layers": layer_results,
            "sanitized_input": sanitized_input,
        }


class SafetyValidator:
    _guardrail = SafetyGuardrail()

    @staticmethod
    def check_command(command: str) -> RiskCheckResult:
        risk_result = RiskScorer.score_risk(command)
        return RiskCheckResult(
            is_safe=risk_result["level"] not in ("high", "critical"),
            risk_level=RiskLevel(risk_result["level"]),
            risk_reasons=risk_result["reasons"],
            suggested_fixes=risk_result["suggestions"],
        )

    @staticmethod
    def check_prompt_injection(prompt: str) -> RiskCheckResult:
        injection_result = InjectionDetector.detect_injection(prompt)
        return RiskCheckResult(
            is_safe=not injection_result["detected"],
            risk_level=RiskLevel(injection_result["risk_level"]),
            risk_reasons=injection_result["patterns_found"],
            suggested_fixes=["请重新组织您的请求，避免使用可能导致注入的措辞"] if injection_result["detected"] else [],
        )

    @staticmethod
    def validate_intent(user_prompt: str, generated_command: str = None) -> Dict[str, Any]:
        result = SafetyValidator._guardrail.validate(user_prompt, generated_command)

        prompt_layer = result["layers"]["injection"]
        command_layer = result["layers"].get("risk_scorer")

        return {
            "is_safe": result["is_safe"],
            "risk_level": result["overall_risk"],
            "prompt_check": {
                "is_safe": prompt_layer["passed"],
                "risk_level": prompt_layer["risk_level"],
                "reasons": prompt_layer["patterns_found"],
                "suggestions": ["请重新组织您的请求，避免使用可能导致注入的措辞"] if not prompt_layer["passed"] else [],
            },
            "command_check": {
                "is_safe": command_layer["passed"],
                "risk_level": command_layer["risk_level"],
                "reasons": command_layer.get("reasons", []),
                "suggestions": command_layer.get("suggestions", []),
            } if command_layer else None,
            "guardrail_report": result,
        }
