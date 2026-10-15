from pathlib import Path

import pandas as pd
import requests


BASE_DIR = Path("./data")
SUPPORTED_ENCODINGS = ("utf-8-sig", "cp949", "euc-kr")

CSV_EXTENSIONS = {".csv", ".tsv"}
EXCEL_EXTENSIONS = {".xlsx", ".xls", ".xlsm", ".xlsb"}

def load_dataset(
    target_file_name: str,
    usecols: list[str] | None = None,
    sheet_name: str | int = 0,
) -> pd.DataFrame:
    """데이터를 pandas의 DataFrame으로 읽어옵니다.
    데이터 파일이 없거나, 인코딩이 잘못되었을 경우 예외가 발생합니다.
    파일은 csv, tsv, 엑셀(xls, xlsx) 파일을 지원합니다.
    인코딩은 utf-8-sig, cp949, euc-kr를 지원합니다.

    Args:
        target_file_name: 확장자를 포함한 파일명을 기재합니다. 구분을 위해 디렉토리를 만들었다면 하위디렉토리까지 포함합니다.
        usecols: 불러오고자하는 데이터에서 특정 컬럼만 사용하고자 한다면 컬럼명을 기재합니다.
        sheet_name: 엑셀파일일 경우 특정 시트(sheet)를 불러오고자 할 경우 해당 시트의 이름을 기재합니다.

    Returns:
        읽어온 데이터 파일을 pandas의 DataFrame으로 반환합니다.
    """

    target_path = BASE_DIR / target_file_name

    if not target_path.is_file():
        raise FileNotFoundError(f'{target_file_name}이 존재하지 않습니다. 디렉토리 혹은 파일명을 확인해주세요')

    extension = target_path.suffix.lower()

    if extension in CSV_EXTENSIONS:
        separator = "\t" if extension == ".tsv" else ","
        decode_errors = []

        for encoding in SUPPORTED_ENCODINGS:
            try:
                return pd.read_csv(
                    target_path,
                    encoding=encoding,
                    sep=separator,
                    usecols=usecols,
                )
            except UnicodeDecodeError as error:
                decode_errors.append(f"{encoding}: {error}")

        raise UnicodeError(f"{target_path} 파일을 읽을 수 없습니다. 파일 혹은 디렉토리를 확인하시기 바랍니다.")

    if extension in EXCEL_EXTENSIONS:
        return pd.read_excel(
            target_path,
            sheet_name=sheet_name,
            usecols=usecols,
        )

    raise ValueError(f"지원하지 않는 파일 확장자입니다: {extension}\n")


def get_api_dataset(
    url: str,
    api_key: str,
    filename: str,
    key_param: str = "serviceKey",
    params: dict[str, str] | None = None,
):
    """공공데이터 API에서 CSV를 받아 프로젝트 루트의 `data/`에 저장합니다.

    Args:
        url: API 기본 URL
        api_key: API 인증키
        filename: 저장할 CSV 파일명
        key_param: API 문서에 명시된 인증키 파라미터 이름
        params: 인증키 외에 API에 전달할 추가 파라미터

    Returns:
        None
    """
    output_name = Path(filename)

    if output_name.name != filename or output_name.suffix.lower() != ".csv":
        raise ValueError("filename에는 경로 없이 .csv 파일명만 지정해 주세요.")

    request_params = dict(params or {})
    request_params[key_param] = api_key

    try:
        response = requests.get(
            url,
            params=request_params,
            timeout=(5, 60),
        )
    except requests.RequestException as error:
        raise RuntimeError(
            f"API 요청 중 오류가 발생했습니다: {type(error).__name__}"
        ) from None

    if not 200 <= response.status_code < 300:
        raise RuntimeError(f"API 요청이 실패했습니다: 응답코드 {response.status_code}")

    if not response.content:
        raise ValueError("API 응답이 비어 있습니다.")

    content_type = response.headers.get("Content-Type", "").lower()
    non_csv_types = ("application/json", "application/xml", "text/xml", "text/html")

    if any(response_type in content_type for response_type in non_csv_types):
        preview = response.content[:300].decode("utf-8", errors="replace")
        raise ValueError(
            "API가 CSV 대신 JSON, XML 또는 HTML을 반환했습니다. "
            "API 문서에서 CSV 응답 형식을 설정할 수 있는지 확인해 주세요.\n\n"
            f"내용: {preview}"
        )

    output_path = BASE_DIR / filename
    output_path.write_bytes(response.content)

    return output_path

