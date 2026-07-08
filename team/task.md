# 🤖 Copilot タスク指示


## タスク: onnx_export.py に新しいアーキテクチャを追加する

対象ファイル: /home/user/GOLF2026/CompressARC/onnx_export.py

TwoLayerConvModelクラスの後、ARCH_REGISTRYの前に以下の6クラスを追加し、ARCH_REGISTRYも更新せよ。既存コードは一切変更しない。

### 追加クラス（one_hot_encode, nn, F, torch は既にimport済み）

class Conv5x5Model(nn.Module):
    def __init__(self):
        super().__init__()
        self.conv = nn.Conv2d(10, 10, kernel_size=5, padding=2, bias=True)
    def forward(self, x):
        return self.conv(one_hot_encode(x))

class DeepConvModel(nn.Module):
    def __init__(self):
        super().__init__()
        self.conv1 = nn.Conv2d(10, 32, 3, padding=1, bias=True)
        self.conv2 = nn.Conv2d(32, 32, 3, padding=1, bias=True)
        self.conv3 = nn.Conv2d(32, 10, 1, bias=True)
    def forward(self, x):
        h = one_hot_encode(x)
        h = F.relu(self.conv1(h))
        h = F.relu(self.conv2(h))
        return self.conv3(h)

class GlobalLocalModel(nn.Module):
    def __init__(self):
        super().__init__()
        self.local_conv = nn.Conv2d(10, 16, 3, padding=1, bias=True)
        self.global_fc  = nn.Linear(10, 16, bias=True)
        self.out_conv   = nn.Conv2d(32, 10, 1, bias=True)
    def forward(self, x):
        h = one_hot_encode(x)
        local = F.relu(self.local_conv(h))
        g = h.mean(dim=[2, 3])
        g = F.relu(self.global_fc(g)).unsqueeze(-1).unsqueeze(-1).expand(-1, -1, h.shape[2], h.shape[3])
        return self.out_conv(torch.cat([local, g], dim=1))

class SmallAttentionModel(nn.Module):
    def __init__(self):
        super().__init__()
        self.embed    = nn.Linear(10, 32, bias=True)
        self.attn     = nn.MultiheadAttention(embed_dim=32, num_heads=4, batch_first=True)
        self.out_proj = nn.Linear(32, 10, bias=True)
    def forward(self, x):
        h = one_hot_encode(x).float()
        B, C, H, W = h.shape
        h = h.permute(0, 2, 3, 1).reshape(B, H * W, C)
        h = self.embed(h)
        h, _ = self.attn(h, h, h)
        h = self.out_proj(h)
        return h.reshape(B, H, W, 10).permute(0, 3, 1, 2)

class WideConvModel(nn.Module):
    def __init__(self):
        super().__init__()
        self.conv1 = nn.Conv2d(10, 64, 3, padding=1, bias=True)
        self.conv2 = nn.Conv2d(64, 64, 3, padding=1, bias=True)
        self.conv3 = nn.Conv2d(64, 64, 3, padding=1, bias=True)
        self.conv4 = nn.Conv2d(64, 64, 3, padding=1, bias=True)
        self.conv5 = nn.Conv2d(64, 10, 1, bias=True)
    def forward(self, x):
        h = one_hot_encode(x)
        for conv in [self.conv1, self.conv2, self.conv3, self.conv4]:
            h = F.relu(conv(h))
        return self.conv5(h)

class LargeAttentionModel(nn.Module):
    def __init__(self):
        super().__init__()
        self.embed    = nn.Linear(10, 64, bias=True)
        self.attn     = nn.MultiheadAttention(embed_dim=64, num_heads=4, batch_first=True)
        self.out_proj = nn.Linear(64, 10, bias=True)
    def forward(self, x):
        h = one_hot_encode(x).float()
        B, C, H, W = h.shape
        h = h.permute(0, 2, 3, 1).reshape(B, H * W, C)
        h = self.embed(h)
        h, _ = self.attn(h, h, h)
        h = self.out_proj(h)
        return h.reshape(B, H, W, 10).permute(0, 3, 1, 2)

### ARCH_REGISTRY の差し替え（既存の4エントリを含め以下に完全置換）
ARCH_REGISTRY = [
    ('color_remap',    ColorRemapModel),
    ('conv1x1',        Conv1x1Model),
    ('conv3x3',        Conv3x3Model),
    ('two_layer_conv', TwoLayerConvModel),
    ('conv5x5',        Conv5x5Model),
    ('deep_conv',      DeepConvModel),
    ('global_local',   GlobalLocalModel),
    ('small_attn',     SmallAttentionModel),
    ('wide_conv',      WideConvModel),
    ('large_attn',     LargeAttentionModel),
]


---
## 完了条件
- 指示されたファイルを全て実装すること
- 実装後は必ず team/report.md に成果物一覧と注意事項を記載すること
