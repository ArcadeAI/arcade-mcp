from datetime import datetime
from typing import Any, Generic, TypeVar

from pydantic import BaseModel, ConfigDict

from arcade.actor.common.response import (
    CustomResponse,
    CustomResponseCode,
)
from arcade.actor.core.conf import settings

_ExcludeData = set[int | str] | dict[int | str, Any]
T = TypeVar("T")


# TODO: Mapping of tool response actions to http codes?


class ToolResponse(BaseModel, Generic[T]):
    """
    Generic unified return model for Tools

    """

    # TODO: json_encoders configuration failure: https://github.com/tiangolo/fastapi/discussions/10252
    model_config = ConfigDict(
        json_encoders={datetime: lambda x: x.strftime(settings.DATETIME_FORMAT)}
    )

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

    async def retry(
        self,
        *,
        res: CustomResponseCode | CustomResponse = CustomResponseCode.HTTP_200,
        msg: str = CustomResponseCode.HTTP_200.msg,
        data: T | None = None,
    ) -> ToolResponse:
        # TODO: Implement retry logic and ability to add messages to the response for
        # the LLM
        return await self.__response(res=res, msg=msg, data=data)

    async def fail(
        self,
        *,
        res: CustomResponseCode | CustomResponse = CustomResponseCode.HTTP_400,
        msg: str = CustomResponseCode.HTTP_400.msg,
        data: Any = None,
    ) -> ToolResponse:
        return await self.__response(res=res, data=data)


tool_response = ToolResponseFactory()
