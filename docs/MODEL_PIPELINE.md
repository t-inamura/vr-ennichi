# マスターからUnity用派生アセットへの変換

## 不変条件

マスターは `outputs/ennichi_50m.blend`。SHA-256は `80f4250595674cb13faeeb7904b8536f2a2963d1924f33a440e32bb53bea4413`。変換前後でハッシュを確認し、違えば停止する。ポインタだけのLFSファイルは拒否する。`build_ennichi.py` や `work/` は実行しない。変換プロセス内での複製・可視性変更だけを行い、マスターをsaveしない。

## 座標

Unityの `(X,Y,Z) = Blenderの(X,Z,Y)`、1単位=1m。Z-up→Y-upの軸交換は反射を伴うので、三角形の頂点順を反転する。負のスケールを持つオブジェクトでは二重反転を補正する。頂点は元オブジェクトのworld matrixを適用してから変換、法線は逆転置行列を使う。Unityでは派生モデルrootを位置0・回転identity・scale1で置く。

訪問領域、店舗BoxCollider、ログも同じ座標系を使う。元manifestのyはUnityのz。店舗は±29.8m、通路中心は±25m。やぐら本体と階段を別の進入禁止Boxで覆う。ベンチ8台は元モデルのboundsからColliderを作る。植栽・装飾の精密な衝突は未実装で、外周は±33mの不可視境界に制限する。

## 形状とマテリアル

共有meshのデータ上のmaterialだけを読むと、同形状のオブジェクトで色が崩れる。変換では**各オブジェクトのeffective material_slotsを複製meshへ割り当てる**。その後、評価済みmesh（modifier/curve/fontを含む）を取り込む。メッシュ化された日本語看板も対象。

`.ennichi` はZIPで、manifestとlittle-endianのindexed meshチャンクを含む。各頂点はposition3、normal3、linear RGBA4。各チャンクはuint32頂点数、uint32 index数、40byte/vertex、uint32 index列。Unity専用ScriptedImporterで読込むため、FBX/glTFの暗黙の軸/scale変換を避ける。形式2を固定し、異なる形式は拒否する。

店舗単位・環境の空間区画単位にまとめ、チャンク内で位置・法線・色が完全一致する頂点を共用する。材質色が異なる頂点を誤って統合しない。各チャンク最大6万頂点、単一の頂点色Shader。元の約1.1万オブジェクトを約352描画チャンクに削減する。三角形自体は約619万のため、**低負荷化が完成したとは言えない**。GPU instancingは採用していない（世界位置に依存するベイク色を保持するため）。性能が不足したらLOD/樹木の簡略化/ライトマップ＋共有mesh方式が次の改修対象。

## 2つの出力モード

| モード | 内容 | 実験開始 |
|---|---|---|
| preview | 実効マテリアルの基本色と簡単な照明。プロシージャル、BOX投影、AREAライトは未再現 | 不可 |
| baked | 元の配置・Generated/Object座標とマテリアルを保持した複製へCycles CPUで静的Diffuse/Direct/Indirect/Emissionを頂点色ベイク | 見た目を別途承認した場合のみ |

```bash
# 形状・軸・看板確認用
blender --background --python tools/export_unity.py -- --appearance preview --output Unity/Assets/Ennichi/Derived/ennichi_preview.ennichi
# 静的照明ベイク、16 samples（この初版の再現設定）
blender --background --python tools/export_unity.py -- --appearance baked --samples 16 --output Unity/Assets/Ennichi/Derived/ennichi_baked.ennichi
python3 tools/check_asset.py Unity/Assets/Ennichi/Derived/ennichi_baked.ennichi
```

`--limit` は変換パイプラインを少数オブジェクトで試すための診断専用で、その出力はUnity importerが拒否する。少数の成功を全モデルの成功と呼ばない。

AREAライト48灯等をUnityへ実時間ライトとして持ち込まない。bakedでは表面への寄与を色として持ち込む。World HDRIの画像は `prepare_project.py` が派生側へコピーし、UnityのPanoramic skyへ設定する。露出0.48と回転の初期値を設定するが、Blenderとの方向・色管理の一致は比較で確認する。素材の帰属は元READMEのPoly Haven CC0表記を維持する。

## 既知の見た目の限界

この初版のベイクは**テクスチャアトラスではなく頂点色**。したがって大きな面の細かな地面テクスチャ、木目、プロシージャルのbump、金属の視点依存反射、水/ガラスの屈折・透過を完全には保持しない。BlenderのAgXとUnityの色管理も一致していない。形状と色差の保存に比べ、材質再現の忠実度は低い。マスターと同等の見た目だと主張しない。

見た目を厳密な実験条件にするなら、**受入を保留し、UVテクスチャ/ライトマップのベイクと水・金属用シェーダーを追加する必要がある**。この点を未検証というだけで隠さず、既知の制限として扱う。

## 視覚・性能の受入

- 元の全景、通路、やぐら、食品、平面の5視点で比較。看板48種、東西南北の配置、左右反転、原寸mを確認。
- 同形状で色違いの食品・箱・提灯を確認。欠落mesh、黒い面、背面の反転、法線の異常を確認。
- 地面の質感・屋台内の明るさ・空の向き・反射/透過の欠落を記録し、研究目的に照らして許容可否を決める。
- 店舗前の領域とColliderの重なり、コーナー通行、やぐら階段のすり抜け、ベンチ衝突を検証。
- 目標PCの解像度・品質・GPUで最低10分の歩行を実施し、フレーム停止・メモリ・欠落率を記録。目標は60fps、20Hz記録だが未達時は性能を改修する。
- 承認する場合だけ派生SHA・確認者・UTC・結果を `visual_review.json` に記録。ファイルの存在だけで通らず、SHAとbaked属性も一致する必要がある。

圧縮ZIPのSHAは時刻メタデータやCPUベイク差で再生成時に変わり得る。クラウドで毎回再ベイクしたモデルに過去の承認を流用しない。再ベイク後のSHAが違えばCIが停止するのは意図した動作。将来、承認済みアセットを固定した成果物置場から取る運用へ変更する場合は、置場・アクセス・費用を別途確認する。
