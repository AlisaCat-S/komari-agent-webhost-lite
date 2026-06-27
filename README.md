# komari-agent-webhost-lite

杩欐槸涓€涓€傜敤浜?Komari 鐨?lite agent锛岄€傚悎涓嶈兘鏂逛究杩愯涓婚」鐩簩杩涘埗 agent 鐨勭幆澧冦€傚綋鍓嶅凡缁忓吋瀹逛富椤圭洰鐨勫畨瑁呭懡浠ゆ牸寮忥紝浣犲彧闇€瑕佹妸浠撳簱鍦板潃鏇挎崲鎴愯繖涓」鐩湴鍧€锛屽氨鍙互鎸変富椤圭洰鐨勪範鎯畨瑁?lite 鐗堛€?

瀹夎鑴氭湰閲囩敤婧愮爜瀹夎鏂瑰紡锛氫細浠庢湰浠撳簱涓嬭浇 `py/komari-agent-python.py` 鍜?`py/requirements.txt`锛屽湪 `/opt/komari-lite` 涓嬪垱寤?Python 铏氭嫙鐜锛屽畨瑁呬緷璧栵紝骞堕€氳繃 `systemd` 鍚姩 lite agent銆?

`pip` 渚濊禆瀹夎浼氳嚜鍔ㄥ湪甯歌鍥藉唴闀滃儚鍜屽畼鏂规簮涔嬮棿鍥為€€鍒囨崲锛涘鏋滀綘瑕佸己鍒舵寚瀹氭簮锛屼篃鍙互鎻愬墠璁剧疆 `PIP_INDEX_URL`銆?

## 瀹夎

鍏煎涓婚」鐩牸寮忕殑瀹夎绀轰緥锛?

```bash
wget -qO- https://ghfast.top/raw.githubusercontent.com/AlisaCat-S/komari-agent-webhost-lite/refs/heads/main/install.sh | sudo bash -s -- -e https://example.com -t TokenXXXXXXXXXXXX --install-ghproxy https://ghfast.top --include-nics eth0
```

鏃х殑鍙屽弬鏁板畨瑁呮柟寮忎粛鐒跺彲鐢細

```bash
sudo bash install.sh https://example.com TokenXXXXXXXXXXXX
```

## 瀹夎鑴氭湰鍙傛暟

| 鍙傛暟 | 璇存槑 |
| --- | --- |
| `-e`, `--endpoint`, `--http-server <url>` | Komari 鏈嶅姟绔湴鍧€ |
| `-t`, `--token <token>` | Komari token |
| `--install-ghproxy <url>` | 涓?raw GitHub 婧愭枃浠朵笅杞芥坊鍔犱唬鐞嗗墠缂€ |
| `--include-nics <list>` | 鍙粺璁℃寚瀹氱綉鍗★紝澶氫釜缃戝崱鐢ㄩ€楀彿鍒嗛殧 |
| `--log-level <level>` | Agent 鏃ュ織绛夌骇 |
| `--disable-web-ssh` | 鍏煎鍙傛暟銆俵ite agent 宸茬Щ闄よ繙绋嬫帶鍒跺姛鑳?|
| `--enable-web-ssh` | 浠呬繚鐣欏吋瀹规€с€俵ite agent 涓嶆彁渚涜繙绋嬫帶鍒跺姛鑳?|

## 瀹夎缁撴灉

瀹夎鑴氭湰浼氬垱寤轰互涓嬪唴瀹癸細

- `/opt/komari-lite/py/komari-agent-python.py`
- `/opt/komari-lite/venv`
- `/etc/systemd/system/komari-agent-lite.service`

## Agent 杩愯鍙傛暟

鎵撳寘鍚庣殑 lite agent 鍚屾椂鏀寔鍘熷闀垮弬鏁板拰涓婚」鐩吋瀹瑰埆鍚嶏細

| 鍙傛暟 | 璇存槑 |
| --- | --- |
| `--http-server <url>` | Komari 鏈嶅姟绔湴鍧€ |
| `-e`, `--endpoint <url>` | `--http-server` 鐨勫埆鍚?|
| `--token <token>` | Komari token |
| `-t <token>` | `--token` 鐨勫埆鍚?|
| `--interval <sec>` | 瀹炴椂涓婃姤闂撮殧 |
| `--reconnect-interval <sec>` | 閲嶈繛闂撮殧 |
| `--include-nics <list>` | 鍙粺璁℃寚瀹氱綉鍗?|
| `--disable-web-ssh` | 鍏煎鍙傛暟銆俵ite agent 宸茬Щ闄よ繙绋嬫帶鍒跺姛鑳?|
| `--enable-web-ssh` | 浠呬繚鐣欏吋瀹规€с€俵ite agent 涓嶆彁渚涜繙绋嬫帶鍒跺姛鑳?|

## 杩滅▼鎺у埗鐘舵€?

lite agent 涓嶅寘鍚繙绋嬫墽琛屽拰缁堢鎺у埗鍔熻兘銆?

- 鏀跺埌鎺у埗浜嬩欢鍚庝細鐩存帴鎷掔粷鎵ц銆?
- `--disable-web-ssh`銆乣--enable-web-ssh`銆乣KOMARI_DISABLE_REMOTE_CONTROL` 浠呯敤浜庡吋瀹逛富椤圭洰椋庢牸鍛戒护鍜屾棫閰嶇疆銆?

## 鐜鍙橀噺

- `KOMARI_HTTP_SERVER`
- `KOMARI_TOKEN`
- `KOMARI_INTERVAL`
- `KOMARI_RECONNECT_INTERVAL`
- `KOMARI_LOG_LEVEL`
- `KOMARI_DISABLE_REMOTE_CONTROL`
- `KOMARI_INCLUDE_NICS`
