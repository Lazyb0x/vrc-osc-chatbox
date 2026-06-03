from typing import Any, ClassVar, Optional


class AppContext:
    """
    全局容器类,用于存储不同类型的对象
    """

    dict_by_name: ClassVar[dict[str, Any]] = {}
    dict_by_type: ClassVar[dict[type, list[Any]]] = {}

    @classmethod
    def add(cls, obj: Any, name: str | None = None) -> None:
        # 没有指定名称，默认使用类型作为名称
        obj_name: str = name if name is not None else obj.__class__.__name__

        if obj_name in cls.dict_by_name:
            raise ValueError(f"An object named '{obj_name}' already exists.")

        cls.dict_by_name[obj_name] = obj
        obj_type = type(obj)
        if obj_type not in cls.dict_by_type:
            cls.dict_by_type[obj_type] = []
        # 列表去除重复对象
        if obj not in cls.dict_by_type[obj_type]:
            cls.dict_by_type[obj_type].append(obj)

    @classmethod
    def remove(cls, obj: Any) -> None:
        name = cls._get_object_name(obj)
        if name:
            cls.remove_by_name(name)
        obj_type = type(obj)
        type_obj_list = cls.dict_by_type.get(obj_type)
        if type_obj_list is not None:
            type_obj_list.remove(obj)

    @classmethod
    def remove_by_name(cls, name: str) -> None:
        obj = cls.dict_by_name.pop(name, None)
        if obj is not None:
            obj_type = type(obj)
            if obj_type in cls.dict_by_type:
                cls.dict_by_type[obj_type].remove(obj)

    @classmethod
    def get(cls, name_or_type: str | type) -> Any | None:
        if isinstance(name_or_type, str):
            return cls.get_by_name(name_or_type)
        if isinstance(name_or_type, type):
            return cls.get_by_type(name_or_type)
        return None

    @classmethod
    def get_by_name(cls, name: str) -> Any | None:
        return cls.dict_by_name.get(name)

    @classmethod
    def get_by_type(cls, obj_type: type) -> Any | None:
        # 可以通过父类找到子类的实例
        for stored_type, obj_list in cls.dict_by_type.items():
            if issubclass(stored_type, obj_type) and obj_list:
                return obj_list[-1]
        return None

    @classmethod
    def _get_object_name(cls, obj: Any) -> str | None:
        for name, stored_obj in cls.dict_by_name.items():
            if stored_obj is obj:
                return name
        return None
