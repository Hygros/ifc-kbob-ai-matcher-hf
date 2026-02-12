import sys, time
print("Python:", sys.version)
start=time.time()
import torch
print("torch version:", torch.__version__)
print("CUDA available:", torch.cuda.is_available())
print("import time:", time.time()-start)

