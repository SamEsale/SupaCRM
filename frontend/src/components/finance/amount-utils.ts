const CURRENCY_PREFIX_PATTERN = /^[\s\u00A0]*[\p{Sc}]+[\s\u00A0]*/u;
const CURRENCY_SUFFIX_PATTERN = /[\s\u00A0]*[\p{Sc}]+[\s\u00A0]*$/u;
const NUMERIC_AMOUNT_PATTERN = /^[+-]?(?:\d+(?:\.\d+)?|\.\d+)$/;
const STRICT_DECIMAL_ALLOWED_CHARS_PATTERN = /[^\d.]/g;
const STRICT_DECIMAL_PATTERN = /^(?:\d+(?:\.\d+)?|\.\d+)$/;
const STRICT_DECIMAL_BLOCKED_KEYS = new Set(["e", "E", "+", "-"]);

export const TOTAL_AMOUNT_REQUIRED_MESSAGE = "Total amount is required.";
export const TOTAL_AMOUNT_INVALID_MESSAGE = "Enter a valid numeric amount.";
export const TOTAL_AMOUNT_NEGATIVE_MESSAGE = "Total amount cannot be negative.";

export interface ParsedMonetaryAmount {
    value: number | null;
    error: string | null;
}

export function parseMonetaryAmountInput(rawValue: string): ParsedMonetaryAmount {
    const trimmed = rawValue.trim();
    if (!trimmed) {
        return { value: null, error: TOTAL_AMOUNT_REQUIRED_MESSAGE };
    }

    const sanitized = trimmed
        .replace(CURRENCY_PREFIX_PATTERN, "")
        .replace(CURRENCY_SUFFIX_PATTERN, "")
        .replace(/,/g, "")
        .trim();

    if (!sanitized) {
        return { value: null, error: TOTAL_AMOUNT_INVALID_MESSAGE };
    }

    if (!NUMERIC_AMOUNT_PATTERN.test(sanitized)) {
        return { value: null, error: TOTAL_AMOUNT_INVALID_MESSAGE };
    }

    const parsed = Number(sanitized);
    if (!Number.isFinite(parsed)) {
        return { value: null, error: TOTAL_AMOUNT_INVALID_MESSAGE };
    }

    if (parsed < 0) {
        return { value: null, error: TOTAL_AMOUNT_NEGATIVE_MESSAGE };
    }

    return { value: parsed, error: null };
}

export function sanitizeStrictDecimalInput(rawValue: string): string {
    const stripped = rawValue.replace(STRICT_DECIMAL_ALLOWED_CHARS_PATTERN, "");
    if (!stripped) {
        return "";
    }

    const [wholePart, ...fractionParts] = stripped.split(".");
    if (fractionParts.length === 0) {
        return wholePart;
    }

    return `${wholePart}.${fractionParts.join("")}`;
}

export function shouldBlockStrictDecimalKey(key: string): boolean {
    return STRICT_DECIMAL_BLOCKED_KEYS.has(key);
}

export function parseStrictDecimalAmountInput(rawValue: string): ParsedMonetaryAmount {
    const trimmed = rawValue.trim();
    if (!trimmed) {
        return { value: null, error: TOTAL_AMOUNT_REQUIRED_MESSAGE };
    }

    const sanitized = trimmed.replace(/,/g, "");
    if (!STRICT_DECIMAL_PATTERN.test(sanitized)) {
        return { value: null, error: TOTAL_AMOUNT_INVALID_MESSAGE };
    }

    const parsed = Number(sanitized);
    if (!Number.isFinite(parsed)) {
        return { value: null, error: TOTAL_AMOUNT_INVALID_MESSAGE };
    }

    if (parsed < 0) {
        return { value: null, error: TOTAL_AMOUNT_NEGATIVE_MESSAGE };
    }

    return { value: parsed, error: null };
}
