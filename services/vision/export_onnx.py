# PharmAi Vision — Designed & developed by NIKHIL CHARY SRIRAMOJU
"""Edge/offline: PyTorch -> ONNX -> INT8 (TensorRT: trtexec --onnx=pillnet.onnx --fp16)."""
import torch
from onnxruntime.quantization import quantize_dynamic, QuantType
from model import PillNet
m = PillNet(5000).eval(); m.load_state_dict(torch.load("pillnet.pt", map_location="cpu"))
torch.onnx.export(m, torch.randn(1, 3, 384, 384), "pillnet.onnx", opset_version=17,
                  input_names=["image"], output_names=["emb", "pill", "shape", "color", "scored"],
                  dynamic_axes={"image": {0: "b"}})
quantize_dynamic("pillnet.onnx", "pillnet.int8.onnx", weight_type=QuantType.QInt8)
