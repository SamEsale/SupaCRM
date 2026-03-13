"""Pagination helpers"""


def paginate(queryset, page: int = 1, per_page: int = 20):
    offset = (page - 1) * per_page
    return queryset[offset: offset + per_page]
