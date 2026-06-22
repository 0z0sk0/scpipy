def scpi_short_length(keyword: str) -> int:
    """
    Return the length of the SCPI short form for a keyword.

    :param keyword: SCPI keyword to analyze.
    :type keyword: str

    :return: Number of characters that belong to the short form.
    :rtype: int
    """
    if len(keyword) < 4:
        return len(keyword)
    return 3 if keyword[3] in 'aeiouAEIOU' else 4


def format_scpi_short_keyword(keyword: str) -> str:
    """
    Format a SCPI keyword in short form.

    :param keyword: SCPI keyword to format.
    :type keyword: str

    :return: Uppercase short-form keyword.
    :rtype: str
    """
    n = scpi_short_length(keyword)
    return keyword[:n].upper()


def format_scpi_full_keyword(keyword: str) -> str:
    """
    Format a SCPI keyword in full form.

    :param keyword: SCPI keyword to format.
    :type keyword: str

    :return: Keyword with the short form in uppercase and the rest in lowercase.
    :rtype: str
    """
    n = scpi_short_length(keyword)
    return keyword[:n].upper() + keyword[n:].lower()
