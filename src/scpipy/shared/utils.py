def scpi_short_length(keyword: str) -> int:
    if len(keyword) < 4:
        return len(keyword)
    return 3 if keyword[3] in 'aeiouAEIOU' else 4


def format_scpi_short_keyword(keyword: str) -> str:
    n = scpi_short_length(keyword)
    return keyword[:n].upper()


def format_scpi_full_keyword(keyword: str) -> str:
    n = scpi_short_length(keyword)
    return keyword[:n].upper() + keyword[n:].lower()
