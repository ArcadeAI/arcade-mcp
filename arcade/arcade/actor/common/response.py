#!/usr/bin/env python3
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict

from arcade.actor.common.response_code import CustomResponse, CustomResponseCode
from arcade.actor.core.conf import settings

_ExcludeData = set[int | str] | dict[int | str, Any]

__all__ = ["ResponseModel", "response_base"]


class ResponseModel(BaseModel):
    """
    # Unified return model
    E.g. ::

        @router.get('/test', response_model=ResponseModel)
        def test():
            return ResponseModel(data={'test': 'test'})

        @router.get('/test')
        def test() -> ResponseModel:
            return ResponseModel(data={'test': 'test'})

        @router.get('/test')
        def test() -> ResponseModel:
            res = CustomResponseCode.HTTP_200
            return ResponseModel(code=res.code, msg=res.msg, data={'test': 'test'})
    """

    # TODO: json_encoders: https://github.com/tiangolo/fastapi/discussions/10252
    model_config = ConfigDict(
        json_encoders={datetime: lambda x: x.strftime(settings.DATETIME_FORMAT)}
    )

    code: int = CustomResponseCode.HTTP_200.code
    msg: str = CustomResponseCode.HTTP_200.msg
    data: Any | None = None


class ResponseBase:
    """
    Unified return method

    .. tip::

        The methods in this class will return the ResponseModel model, existing as a coding style;

    E.g. ::

        @router.get('/test')
        def test() -> ResponseModel:
            return await response_base.success(data={'test': 'test'})
    """

    @staticmethod
    async def __response(
        *,
        res: CustomResponseCode | CustomResponse = CustomResponseCode.HTTP_200,
        msg: str | None = None,
        data: Any | None = None,
    ) -> ResponseModel:
        """
        General method for successful response

        :param res: Response information
        :param data: Response data
        :return:
        """
        msg = msg if msg else res.msg
        return ResponseModel(code=res.code, msg=msg, data=data)

    async def success(
        self,
        *,
        res: CustomResponseCode | CustomResponse = CustomResponseCode.HTTP_200,
        data: Any | None = None,
    ) -> ResponseModel:
        return await self.__response(res=res, data=data)

    async def fail(
        self,
        *,
        res: CustomResponseCode | CustomResponse = CustomResponseCode.HTTP_400,
        data: Any = None,
    ) -> ResponseModel:
        return await self.__response(res=res, data=data)

    async def error(
        self,
        *,
        res: CustomResponseCode | CustomResponse = CustomResponseCode.HTTP_400,
        msg: str = CustomResponseCode.HTTP_400.msg,
        data: Any = None,
    ) -> ResponseModel:
        return await self.__response(res=res, msg=msg, data=data)


response_base = ResponseBase()
