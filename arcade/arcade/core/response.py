from typing import Any, Generic, TypeVar

from pydantic import BaseModel

from arcade.core.response_code import (
    CustomResponse,
    CustomResponseCode,
)

_ExcludeData = set[int | str] | dict[int | str, Any]
T = TypeVar("T")


# TODO: Mapping of tool response actions to http codes?


class ToolResponse(BaseModel, Generic[T]):
    """
    Generic unified return model for Tools

    """

    code: int = CustomResponseCode.HTTP_200.code
    msg: str = CustomResponseCode.HTTP_200.msg

    #
    data: T | None = None


class ToolResponseFactory:
    """
    Singleton pattern for unified return method from tools.
    """

    @staticmethod
    async def __response(
        *,
        msg: str | None = None,
        res: CustomResponseCode | CustomResponse = CustomResponseCode.HTTP_200,
        data: T | None = None,
    ) -> ToolResponse:
        """
        General method for successful response
        """
        if msg:
            return ToolResponse(code=res.code, msg=msg, data=data)
        return ToolResponse(code=res.code, msg=res.msg, data=data)

    async def success(
        self,
        *,
        res: CustomResponseCode | CustomResponse = CustomResponseCode.HTTP_200,
        data: T | None = None,
    ) -> ToolResponse:
        return await self.__response(res=res, data=data)

    async def fail(
        self,
        *,
        res: CustomResponseCode | CustomResponse = CustomResponseCode.HTTP_400,
        msg: str = CustomResponseCode.HTTP_400.msg,
        data: Any = None,
    ) -> ToolResponse:
        return await self.__response(
            res=res,
            msg=msg,  # TODO this needs to map to developer_message in output.error
            data=data,
        )


tool_response = ToolResponseFactory()
