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
    additional_prompt_content: str | None = None

    #
    data: T | None = None


class ToolResponseFactory:
    """
    Singleton pattern for unified return method from tools.
    """

    @staticmethod
    def __response(
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

    def success(
        self,
        *,
        res: CustomResponseCode | CustomResponse = CustomResponseCode.HTTP_200,
        data: T | None = None,
    ) -> ToolResponse:
        return self.__response(res=res, data=data)

    def fail(
        self,
        *,
        res: CustomResponseCode | CustomResponse = CustomResponseCode.HTTP_400,
        msg: str = CustomResponseCode.HTTP_400.msg,
        data: Any = None,
    ) -> ToolResponse:
        return self.__response(
            res=res,
            msg=msg,  # TODO this needs to map to developer_message in output.error
            data=data,
        )

    def fail_retry(
        self,
        *,
        res: CustomResponseCode | CustomResponse = CustomResponseCode.HTTP_425,
        msg: str = CustomResponseCode.HTTP_425.msg,
        data: Any = None,
        additional_prompt_content: str | None = None,
    ) -> ToolResponse:
        res = self.__response(
            res=res,
            msg=msg,
            data=data,
        )
        res.additional_prompt_content = additional_prompt_content
        return res


tool_response = ToolResponseFactory()
