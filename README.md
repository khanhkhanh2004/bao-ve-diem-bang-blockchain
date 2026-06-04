# 

<h3 align="center">ỨNG DỤNG BLOCKCHAIN TRONG ĐẢM BẢO TÍNH TOÀN VẸN DỮ LIỆU ĐIỂM SINH VIÊN</h3>

<div align="center">

<p align="center">
  <img src="dnu_logo.png" alt="DaiNam University Logo" width="200"/>
  <img src="khoa_cntt.png" alt="AIoTLab Logo" width="170"/>
</p>
</div>


<div align="center">

<img src="images/congnghesudung.png" alt="Công nghệ sử dụng" width="850"/>

</div>

## 1. Cài thư viện

```bash
pip install -r requirements.txt
```

## 2. Bật Ganache

Mở Ganache, tạo workspace nhanh.

RPC thường là:

```text
http://127.0.0.1:7545
```

Nếu Ganache của bạn dùng cổng khác, sửa lại trong `contract_config.json`.

## 3. Deploy Smart Contract bằng Remix

Mở Remix:

```text
https://remix.ethereum.org
```

Tạo file:

```text
GradeStorage.sol
```

Copy code trong:

```text
contracts/GradeStorage.sol
```

Compile bằng Solidity 0.8.x.

Deploy:

- Environment: Injected Provider - MetaMask hoặc Ganache Provider nếu Remix hỗ trợ
- Nếu dùng MetaMask: kết nối MetaMask vào mạng Ganache
- Deploy contract

Sau khi deploy, copy:

- Contract address
- ABI trong mục Compilation Details

## 4. Tạo file contract_config.json

Copy file:

```text
contract_config.example.json
```

đổi tên thành:

```text
contract_config.json
```

Sửa nội dung:

```json
{
  "ganache_url": "http://127.0.0.1:7545",
  "contract_address": "ĐỊA_CHỈ_CONTRACT_SAU_KHI_DEPLOY",
  "abi": DÁN_ABI_VÀO_ĐÂY
}
```

Lưu ý: ABI là một mảng JSON, không để trong dấu nháy.

## 5. Chạy app

```bash
python app.py
```

Mở:

```text
http://127.0.0.1:5000
```

## 6. Cách Sử Dụng

### Trường hợp 1: nhập điểm

Nhập:

- Mã SV: SV001
- Tên: Nguyễn Văn A
- Môn: Blockchain
- Điểm: 8.5
- Học kỳ: HK1 2025-2026

Hệ thống sẽ:

1. Lưu điểm vào SQLite
2. Tạo hash SHA-256
3. Ghi hash lên smart contract trên Ganache
4. Lưu transaction hash vào log

### Trường hợp 2: cập nhật điểm hợp lệ

Vào chi tiết, cập nhật điểm 8.5 thành 9.0, lý do “Phúc khảo”.

Hệ thống sẽ:

1. Cập nhật điểm trong database
2. Tạo hash mới
3. Ghi hash mới lên blockchain
4. Lưu lịch sử giao dịch

### Trường hợp 3: sửa lén database

Bấm chức năng “Sửa database không ghi blockchain”.

Hệ thống chỉ sửa điểm trong SQLite, không ghi blockchain.

Khi xác minh, hash tính từ database sẽ khác hash mới nhất trên blockchain, nên app báo:

```text
Dữ liệu đã bị thay đổi
```

## 8. Lưu ý quan trọng

- SQLite lưu điểm thật.
- Blockchain chỉ lưu hash, không lưu toàn bộ điểm.
- Mỗi lần cập nhật điểm hợp lệ sẽ tạo transaction mới trên blockchain.
- Nếu reset database nhưng không reset Ganache, blockchain vẫn còn dữ liệu cũ.
