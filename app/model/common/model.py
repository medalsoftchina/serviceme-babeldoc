from fastapi import Query

class PaginationParams:
    """
    Pagination parameters for a list of items.
    # 用法示例
    """

    def __init__(
        # 暂时先放开到500，为了解决某些bug
        self,
        page: int = Query(1, gt=0),
        page_size: int = Query(10, gt=0, le=500),
    ):
        self.page = page
        self.page_size = page_size
        self.skip = (page - 1) * page_size