from django.db.models import QuerySet


def page_of_queryset(queryset: QuerySet, page: int, num: int) -> QuerySet:
    """
    :param queryset: QuerySet
    :param page: page num
    :param num: item num of each page
    :return: the required QuerySet
    """
    return queryset[(page-1)*num:page*num]