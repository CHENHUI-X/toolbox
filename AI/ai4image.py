import os
import requests
from typing import Optional
from urllib.parse import urlparse



def save_image(
    url: str,
    save_dir: str = "./image",
) -> str:
    """
    下载图片并无损保存到本地

    Args:
        url:
            图片链接

        save_dir:
            保存目录

            默认:
                当前路径下的 image 文件夹

    Returns:
        保存后的本地文件完整路径


    说明:
        无损保存 = 直接写入原始字节(response.content),
        不做任何二次编码/转码/压缩,
        保证和原图完全一致

        文件名:
            取自 URL 中的文件名
            (例如 d939ecd5-xxx.png => d939ecd5-xxx.png)
    """

    # 创建保存目录(不存在则自动创建)
    os.makedirs(save_dir, exist_ok=True)


    # 下载图片
    response = requests.get(
        url,
        timeout=60,
    )

    response.raise_for_status()


    # 取 URL 中的文件名(包含扩展名)
    filename = os.path.basename(
        urlparse(url).path
    )


    # 防止 URL 没有文件名的情况
    if not filename:
        filename = "image.png"


    save_path = os.path.join(
        save_dir,
        filename,
    )


    # 无损写入:直接保存原始字节,不经过任何图像库处理
    with open(save_path, "wb") as f:
        f.write(response.content)


    print(f"图片已保存: {save_path}")

    return save_path

class GPTImageClient:
    """
    GPT Image API Client

    支持:
        1. generate()
            文生图

        2. edit()
            图片编辑

    """

    def __init__(
        self,
        api_key: str,
        base_url: str = "https://www.packyapi.com/v1/images",
    ):
        """
        初始化客户端

        Args:
            api_key:
                API Token

            base_url:
                图片接口地址
        """

        self.base_url = base_url

        self.headers = {
            "Authorization": f"Bearer {api_key}",
            "Accept": "*/*",
        }


    @staticmethod
    def _parse_image_url(response: dict) -> str:
        """
        解析接口返回的图片URL

        返回格式:

        {
            "data": [
                {
                    "url": "xxx"
                }
            ]
        }
        """

        return response["data"][0]["url"]


    @staticmethod
    def _is_url(path: str) -> bool:
        """
        判断输入是否为URL
        """

        return urlparse(path).scheme in (
            "http",
            "https",
        )


    def _load_image(self, image: str):
        """
        加载图片

        支持:

        1. 本地文件

            image="demo.png"


        2. 图片URL

            image="https://xxx/demo.png"


        如果输入URL:

            自动下载图片

            并保留原始文件名:

            https://xxx/files/demo.png

            =>
            demo.png

        """

        if self._is_url(image):

            response = requests.get(
                image,
                timeout=60,
            )

            response.raise_for_status()


            # 获取URL中的文件名
            filename = os.path.basename(
                urlparse(image).path
            )


            # 防止URL没有文件名
            if not filename:
                filename = "image.png"


            return (
                filename,
                response.content,
                response.headers.get(
                    "Content-Type",
                    "image/png",
                ),
            )


        # 本地文件
        with open(image, "rb") as f:

            return (
                os.path.basename(image),
                f.read(),
                "image/png",
            )


    def generate(
        self,
        prompt: str,
        model: str = "gpt-image-2",
        n: int = 1,
        size: str = "auto",
        quality: str = "medium",
        response_format: str = "url",
        output_format: str = "png",
        output_compression: Optional[int] = None,
        # 官网示例接口没有传这两个字段,packyapi 可能未适配,
        # 默认不传,避免触发后端 500;需要时可显式传入
        background: Optional[str] = None,
        moderation: Optional[str] = None,
        user: Optional[str] = None,
    ) -> str:
        """
        文生图


        Args:

            model:
                图片生成模型

                固定:
                    gpt-image-2


            prompt:
                图片描述提示词

                建议包含:

                    主体
                    场景
                    风格
                    布局
                    比例
                    文字内容


            n:
                返回图片数量

                当前接口:
                    仅支持1


            size:
                图片尺寸

                支持:

                    auto

                    1024x1024

                    1536x1024

                    1024x1536

                    1536x864

                    3840x2160


                PPT推荐:

                    3840x2160


            quality:
                图片质量

                可选:

                    low
                    medium
                    high
                    auto


                high:
                    正式输出


            response_format:
                返回格式

                url:
                    返回图片链接

                b64_json:
                    返回base64


            output_format:
                输出格式

                推荐:

                    png

                png:
                    无损
                    文字清晰


            output_compression:
                图片压缩比例

                范围:

                    0~100

                仅jpeg有效


            background:
                背景

                opaque:
                    不透明背景

                官网示例未携带该字段,
                默认不传(None),
                需要时再显式指定


            moderation:
                安全审核

                auto:
                    默认

                官网示例未携带该字段,
                默认不传(None),
                需要时再显式指定


            user:
                用户标识

        """


        payload = {
            "model": model,
            "prompt": prompt,
            "n": n,
            "size": size,
            "quality": quality,
            "response_format": response_format,
            "output_format": output_format,
        }


        if output_compression is not None:
            payload["output_compression"] = (
                output_compression
            )


        if background is not None:
            payload["background"] = background


        if moderation is not None:
            payload["moderation"] = moderation


        if user is not None:
            payload["user"] = user



        response = requests.post(
            f"{self.base_url}/generations",
            headers={
                **self.headers,
                "Content-Type": "application/json",
            },
            json=payload,
            timeout=300,
        )


        if not response.ok:
            # 打印/抛出服务端返回的具体错误信息,
            # 而不是只报一个 500,方便定位问题
            raise RuntimeError(
                f"请求失败: {response.status_code} "
                f"{response.text}"
            )


        return self._parse_image_url(
            response.json()
        )



    def edit(
        self,
        image: str,
        prompt: str,
        model: str = "gpt-image-2",
        mask_path: Optional[str] = None,
        n: int = 1,
        size: str = "auto",
        quality: str = "medium",
        response_format: str = "url",
        output_format: str = "png",
        output_compression: Optional[int] = None,
        # 同 generate(),默认不传,避免触发后端 500;
        # 需要时可显式传入
        background: Optional[str] = None,
        moderation: Optional[str] = None,
        input_fidelity: Optional[str] = None,
        user: Optional[str] = None,
    ) -> str:
        """
        图片编辑


        Args:

            image:
                原始图片

                支持:

                    本地路径

                    图片URL


                例如:

                    xxx.png

                    https://xxx/image.png



            prompt:
                编辑要求

                推荐说明:

                    保留什么

                    修改什么

                    最终效果



            mask_path:
                局部修改区域

                PNG mask

                不传:

                    默认整图编辑



            input_fidelity:
                原图保持程度


                high:

                    最大程度保持:

                        原图结构
                        主体
                        细节


                PPT修改推荐:

                    high

                默认不传(None),
                需要时再显式指定为 "high"



            其他参数:

                与generate一致

                background / moderation
                默认不传(None),
                需要时再显式指定

        """

        data = {
            "model": model,
            "prompt": prompt,
            "n": n,
            "size": size,
            "quality": quality,
            "response_format": response_format,
            "output_format": output_format,
        }


        if output_compression is not None:
            data["output_compression"] = (
                output_compression
            )


        if background is not None:
            data["background"] = background


        if moderation is not None:
            data["moderation"] = moderation


        if input_fidelity is not None:
            data["input_fidelity"] = input_fidelity


        if user is not None:
            data["user"] = user



        filename, image_bytes, content_type = (
            self._load_image(image)
        )


        files = {
            "image": (
                filename,
                image_bytes,
                content_type,
            )
        }



        if mask_path:

            files["mask"] = (
                os.path.basename(mask_path),
                open(mask_path, "rb"),
                "image/png",
            )



        try:

            response = requests.post(
                f"{self.base_url}/edits",
                headers=self.headers,
                files=files,
                data=data,
                timeout=300,
            )


            if not response.ok:
                # 同 generate(),把服务端的具体错误信息抛出来
                raise RuntimeError(
                    f"请求失败: {response.status_code} "
                    f"{response.text}"
                )


            return self._parse_image_url(
                response.json()
            )


        finally:

            # 关闭mask文件句柄
            if mask_path:
                files["mask"][1].close()
