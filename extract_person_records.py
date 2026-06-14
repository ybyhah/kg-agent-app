from __future__ import annotations

import argparse
from pathlib import Path

from src.information_extraction import PersonRecordExtractor, extract_records_to_file
from src.local_llm import LocalTransformersLangChainClient


def build_argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="使用本地 Xunzi-Qwen3-8B-base 模型对人物 JSON 做 NER、属性抽取、关系抽取。"
    )
    parser.add_argument(
        "--input",
        default="person_records_v5.json",
        help="输入 JSON 文件路径，默认使用当前目录下的 person_records_v5.json",
    )
    parser.add_argument(
        "--output",
        default="data/intermediate/person_records_v5_extractions.json",
        help="输出 JSON 文件路径",
    )
    parser.add_argument(
        "--model-dir",
        default=r"D:\models\Xunzi-Qwen3-8B-base",
        help="本地模型目录",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="只处理前 N 条记录，便于调试",
    )
    parser.add_argument(
        "--max-new-tokens",
        type=int,
        default=768,
        help="模型每次生成的最大 token 数",
    )
    parser.add_argument(
        "--temperature",
        type=float,
        default=0.1,
        help="生成温度，默认偏低以稳定结构化输出",
    )
    parser.add_argument(
        "--device",
        default="auto",
        help="transformers 设备设置，默认 auto",
    )
    parser.add_argument(
        "--load-in-4bit",
        action="store_true",
        help="尝试以 4-bit 量化加载模型，适合显存较小的机器",
    )
    return parser


def main() -> None:
    parser = build_argument_parser()
    args = parser.parse_args()

    base_dir = Path(__file__).resolve().parent
    input_path = (base_dir / args.input).resolve()
    output_path = (base_dir / args.output).resolve()
    model_dir = Path(args.model_dir).resolve()

    client = LocalTransformersLangChainClient(
        model_dir=model_dir,
        max_new_tokens=args.max_new_tokens,
        temperature=args.temperature,
        device=args.device,
        load_in_4bit=args.load_in_4bit,
    )
    extractor = PersonRecordExtractor(client=client)
    extract_records_to_file(
        input_path=input_path,
        output_path=output_path,
        extractor=extractor,
        limit=args.limit,
    )
    print(f"Extraction written to: {output_path}")


if __name__ == "__main__":
    main()
