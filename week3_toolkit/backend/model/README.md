# Model files

The trained model weights are not stored in the Git repository.

Place these files in this directory before starting the backend:

| File | Size | SHA-256 |
|---|---:|---|
| `rafdb_emotion.pt` | 269.62 MB | `08460F14D1639CD9245A8EFE329C8B9E36EA108EA665D3D59D78EB331CB641A3` |
| `yolo_face.pt` | 5.94 MB | `6C6CCFA0BA0FEA2C5D6AE1F0AF3497B0FD0CE784339423F64DD6B47EBFC2BCC8` |

Verify a downloaded file with PowerShell:

```powershell
Get-FileHash .\rafdb_emotion.pt -Algorithm SHA256
Get-FileHash .\yolo_face.pt -Algorithm SHA256
```

Before redistributing either file, confirm that the original face model,
training dataset, and derived checkpoint licenses permit distribution.

For public releases, attach the model files to a GitHub Release or host them
in object storage. Do not commit the large checkpoint directly to normal Git.
