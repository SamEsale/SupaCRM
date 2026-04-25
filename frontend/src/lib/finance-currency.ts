import type { Tenant } from "@/types/tenants";

export interface SecondaryCurrencyDisplay {
    convertedAmountLabel: string;
    convertedCurrency: string;
    rateLabel: string;
    sourceLabel: string;
    asOfLabel: string;
}

function formatMoney(amount: number, currency: string): string {
    if (!Number.isFinite(amount)) {
        return `${amount} ${currency}`;
    }

    return new Intl.NumberFormat("en-US", {
        style: "currency",
        currency,
    }).format(amount);
}

function formatRateSource(value: string | null | undefined): string {
    if (!value) {
        return "Unknown";
    }

    return value
        .split("_")
        .join(" ")
        .split(" ")
        .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
        .join(" ");
}

function formatAsOf(value: string): string {
    const parsed = new Date(value);
    if (Number.isNaN(parsed.getTime())) {
        return value;
    }
    return parsed.toLocaleString("en-US");
}

function normalizeCurrency(value: string | null | undefined): string | null {
    if (!value) {
        return null;
    }
    const normalized = value.trim().toUpperCase();
    return /^[A-Z]{3}$/.test(normalized) ? normalized : null;
}

function parseRate(value: string | null | undefined): number | null {
    if (!value) {
        return null;
    }
    const parsed = Number(value);
    return Number.isFinite(parsed) && parsed > 0 ? parsed : null;
}

export function getSecondaryCurrencyDisplay(
    tenant: Tenant | null | undefined,
    amount: string,
    currency: string,
): SecondaryCurrencyDisplay | null {
    const defaultCurrency = normalizeCurrency(tenant?.default_currency);
    const secondaryCurrency = normalizeCurrency(tenant?.secondary_currency);
    const normalizedAmountCurrency = normalizeCurrency(currency);
    const rate = parseRate(tenant?.secondary_currency_rate);
    const source = tenant?.secondary_currency_rate_source ?? null;
    const asOf = tenant?.secondary_currency_rate_as_of ?? null;
    const numericAmount = Number(amount);

    if (
        !defaultCurrency
        || !secondaryCurrency
        || defaultCurrency === secondaryCurrency
        || !normalizedAmountCurrency
        || !rate
        || !source
        || !asOf
        || !Number.isFinite(numericAmount)
    ) {
        return null;
    }

    let convertedAmount = 0;
    let convertedCurrency = "";

    if (normalizedAmountCurrency === defaultCurrency) {
        convertedAmount = numericAmount * rate;
        convertedCurrency = secondaryCurrency;
    } else if (normalizedAmountCurrency === secondaryCurrency) {
        convertedAmount = numericAmount / rate;
        convertedCurrency = defaultCurrency;
    } else {
        return null;
    }

    return {
        convertedAmountLabel: formatMoney(convertedAmount, convertedCurrency),
        convertedCurrency,
        rateLabel: `1 ${defaultCurrency} = ${rate.toFixed(6)} ${secondaryCurrency}`,
        sourceLabel: formatRateSource(source),
        asOfLabel: formatAsOf(asOf),
    };
}

export function getMissingSecondaryCurrencyRateMessage(
    tenant: Tenant | null | undefined,
    currency: string,
): string | null {
    const defaultCurrency = normalizeCurrency(tenant?.default_currency);
    const secondaryCurrency = normalizeCurrency(tenant?.secondary_currency);
    const normalizedAmountCurrency = normalizeCurrency(currency);
    const hasRate = parseRate(tenant?.secondary_currency_rate);

    if (!secondaryCurrency || hasRate || !normalizedAmountCurrency) {
        return null;
    }

    if (normalizedAmountCurrency !== defaultCurrency && normalizedAmountCurrency !== secondaryCurrency) {
        return null;
    }

    return `Secondary currency is configured for ${secondaryCurrency}, but no manual exchange rate has been saved yet.`;
}
