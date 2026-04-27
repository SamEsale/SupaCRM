const COUNTRY_OPTIONS = [
    "Afghanistan",
    "Albania",
    "Algeria",
    "Andorra",
    "Angola",
    "Antigua and Barbuda",
    "Argentina",
    "Armenia",
    "Australia",
    "Austria",
    "Azerbaijan",
    "Bahamas",
    "Bahrain",
    "Bangladesh",
    "Barbados",
    "Belarus",
    "Belgium",
    "Belize",
    "Benin",
    "Bhutan",
    "Bolivia",
    "Bosnia and Herzegovina",
    "Botswana",
    "Brazil",
    "Brunei",
    "Bulgaria",
    "Burkina Faso",
    "Burundi",
    "Cabo Verde",
    "Cambodia",
    "Cameroon",
    "Canada",
    "Central African Republic",
    "Chad",
    "Chile",
    "China",
    "Colombia",
    "Comoros",
    "Congo",
    "Costa Rica",
    "Cote d'Ivoire",
    "Croatia",
    "Cuba",
    "Cyprus",
    "Czech Republic",
    "Democratic Republic of the Congo",
    "Denmark",
    "Djibouti",
    "Dominica",
    "Dominican Republic",
    "Ecuador",
    "Egypt",
    "El Salvador",
    "Equatorial Guinea",
    "Eritrea",
    "Estonia",
    "Eswatini",
    "Ethiopia",
    "Fiji",
    "Finland",
    "France",
    "Gabon",
    "Gambia",
    "Georgia",
    "Germany",
    "Ghana",
    "Greece",
    "Grenada",
    "Guatemala",
    "Guinea",
    "Guinea-Bissau",
    "Guyana",
    "Haiti",
    "Honduras",
    "Hungary",
    "Iceland",
    "India",
    "Indonesia",
    "Iran",
    "Iraq",
    "Ireland",
    "Israel",
    "Italy",
    "Jamaica",
    "Japan",
    "Jordan",
    "Kazakhstan",
    "Kenya",
    "Kiribati",
    "Kuwait",
    "Kyrgyzstan",
    "Laos",
    "Latvia",
    "Lebanon",
    "Lesotho",
    "Liberia",
    "Libya",
    "Liechtenstein",
    "Lithuania",
    "Luxembourg",
    "Madagascar",
    "Malawi",
    "Malaysia",
    "Maldives",
    "Mali",
    "Malta",
    "Marshall Islands",
    "Mauritania",
    "Mauritius",
    "Mexico",
    "Micronesia",
    "Moldova",
    "Monaco",
    "Mongolia",
    "Montenegro",
    "Morocco",
    "Mozambique",
    "Myanmar",
    "Namibia",
    "Nauru",
    "Nepal",
    "Netherlands",
    "New Zealand",
    "Nicaragua",
    "Niger",
    "Nigeria",
    "North Korea",
    "North Macedonia",
    "Norway",
    "Oman",
    "Pakistan",
    "Palau",
    "Panama",
    "Papua New Guinea",
    "Paraguay",
    "Peru",
    "Philippines",
    "Poland",
    "Portugal",
    "Qatar",
    "Republic of Korea",
    "Romania",
    "Russian Federation",
    "Rwanda",
    "Saint Kitts and Nevis",
    "Saint Lucia",
    "Saint Vincent and the Grenadines",
    "Samoa",
    "San Marino",
    "Sao Tome and Principe",
    "Saudi Arabia",
    "Senegal",
    "Serbia",
    "Seychelles",
    "Sierra Leone",
    "Singapore",
    "Slovakia",
    "Slovenia",
    "Solomon Islands",
    "Somalia",
    "South Africa",
    "South Sudan",
    "Spain",
    "Sri Lanka",
    "Sudan",
    "Suriname",
    "Sweden",
    "Switzerland",
    "Syrian Arab Republic",
    "Tajikistan",
    "Tanzania",
    "Thailand",
    "Timor-Leste",
    "Togo",
    "Tonga",
    "Trinidad and Tobago",
    "Tunisia",
    "Turkey",
    "Turkmenistan",
    "Tuvalu",
    "Uganda",
    "Ukraine",
    "United Arab Emirates",
    "United Kingdom",
    "United States",
    "Uruguay",
    "Uzbekistan",
    "Vanuatu",
    "Venezuela",
    "Viet Nam",
    "Yemen",
    "Zambia",
    "Zimbabwe",
];

export interface CompanyAddressFields {
    street: string;
    unit: string;
    postalCode: string;
    city: string;
    stateCounty: string;
    country: string;
}

function normalizePart(value: string | null | undefined): string {
    return (value ?? "").trim();
}

function splitLegacyLine(value: string): [string, string] {
    const parts = value.split(/,\s*/).map((part) => part.trim()).filter(Boolean);
    if (parts.length >= 2) {
        return [parts[0], parts.slice(1).join(", ")];
    }

    return [value.trim(), ""];
}

function parsePostalCity(value: string): { postalCode: string; city: string } {
    const trimmed = value.trim();
    if (!trimmed) {
        return { postalCode: "", city: "" };
    }

    const match = trimmed.match(/^(\d[\d\s-]*?)\s+(.+)$/u);
    if (match) {
        return {
            postalCode: match[1].trim(),
            city: match[2].trim(),
        };
    }

    return {
        postalCode: "",
        city: trimmed,
    };
}

function splitSerializedAddress(address: string): string[] {
    const normalized = address.trim();
    if (!normalized) {
        return [];
    }

    if (normalized.includes(" | ")) {
        return normalized.split(" | ").map((part) => part.trim());
    }

    if (normalized.includes("\n")) {
        return normalized.split("\n").map((part) => part.trim());
    }

    return normalized.split(" ; ").map((part) => part.trim()).filter(Boolean);
}

export function getCountryOptions(): string[] {
    return COUNTRY_OPTIONS;
}

export function formatCompanyAddress(address: string | null | undefined): string {
    const parsed = parseCompanyAddress(address);
    const segments = [
        parsed.street,
        parsed.unit,
        [parsed.postalCode, parsed.city].filter(Boolean).join(" "),
        parsed.stateCounty,
        parsed.country,
    ].filter((segment) => segment.trim().length > 0);

    return segments.join(", ");
}

export function parseCompanyAddress(address: string | null | undefined): CompanyAddressFields {
    if (!address || !address.trim()) {
        return {
            street: "",
            unit: "",
            postalCode: "",
            city: "",
            stateCounty: "",
            country: "Sweden",
        };
    }

    const parts = splitSerializedAddress(address);

    if (parts.length >= 5) {
        const [streetPart, unitPart, postalCityPart, stateCountyPart, countryPart] = parts;
        const postalCity = parsePostalCity(postalCityPart);

        return {
            street: streetPart.trim(),
            unit: unitPart.trim(),
            postalCode: postalCity.postalCode,
            city: postalCity.city,
            stateCounty: stateCountyPart.trim(),
            country: countryPart.trim() || "Sweden",
        };
    }

    if (parts.length === 4) {
        const [streetPart, postalCityPart, stateCountyPart, countryPart] = parts;
        const [street, unit] = splitLegacyLine(streetPart);
        const postalCity = parsePostalCity(postalCityPart);

        return {
            street,
            unit,
            postalCode: postalCity.postalCode,
            city: postalCity.city,
            stateCounty: stateCountyPart.trim(),
            country: countryPart.trim() || "Sweden",
        };
    }

    if (parts.length === 3) {
        const [streetPart, postalCityPart, countryPart] = parts;
        const [street, unit] = splitLegacyLine(streetPart);
        const postalCity = parsePostalCity(postalCityPart);

        return {
            street,
            unit,
            postalCode: postalCity.postalCode,
            city: postalCity.city,
            stateCounty: "",
            country: countryPart.trim() || "Sweden",
        };
    }

    if (parts.length === 2) {
        const [streetPart, postalCityPart] = parts;
        const [street, unit] = splitLegacyLine(streetPart);
        const postalCity = parsePostalCity(postalCityPart);

        return {
            street,
            unit,
            postalCode: postalCity.postalCode,
            city: postalCity.city,
            stateCounty: "",
            country: "Sweden",
        };
    }

    return {
        street: address.trim(),
        unit: "",
        postalCode: "",
        city: "",
        stateCounty: "",
        country: "Sweden",
    };
}

export function buildCompanyAddress(fields: CompanyAddressFields): string | null {
    const street = normalizePart(fields.street);
    const unit = normalizePart(fields.unit);
    const postalCode = normalizePart(fields.postalCode);
    const city = normalizePart(fields.city);
    const stateCounty = normalizePart(fields.stateCounty);
    const country = normalizePart(fields.country);

    const parts = [street, unit, [postalCode, city].filter(Boolean).join(" "), stateCounty, country];

    if (!street && !unit && !postalCode && !city && !stateCounty) {
        return null;
    }

    return parts.join("\n");
}
