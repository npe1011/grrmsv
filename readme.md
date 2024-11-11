# GRRM Log Viewer (シングルジョブ用)

GRRMの単一ログファイル形式の計算結果の可視化用GUIツールです。可視化できるのは、MIN, MIN+AFIR SADDLE, IRC, LUP, SADDLE+IRCなどの単一のログファイルが出力されるタイプのジョブです。
MC-AFIRの個別のファイルも (*_EQn.log) もMIN+AFIRと同じ形式なので一応読めるとは思います (動作保証外。テストろくにしていません)。また特殊な複合ジョブ等は対応外です。
全体的にデバッグ不足なので、想定外のパターンのログが来ると動作がおかしいかもです。


- [GRRM Log Viewer (シングルジョブ用)](#grrm-log-viewer-シングルジョブ用)
  - [1. 動作環境](#1-動作環境)
    - [1.1. 更新履歴（適当）](#11-更新履歴適当)
      - [2024/11/11](#20241111)
      - [2024/1/13](#2024113)
    - [1.2. 外部ビューワの設定](#12-外部ビューワの設定)
    - [1.3. 動作テスト環境](#13-動作テスト環境)
  - [2. 利用方法](#2-利用方法)
    - [2.1. OPT (MIN/SADDLE)](#21-opt-minsaddle)
    - [2.2. FREQ](#22-freq)
    - [2.3. IRC](#23-irc)
    - [2.4. MIN+AFIR](#24-minafir)
    - [2.5. LUP](#25-lup)
  - [3. 設定](#3-設定)
  - [4. デバッグ](#4-デバッグ)

## 1. 動作環境

### 1.1. 更新履歴（適当）

#### 2024/11/11
- 公開
- Thermochemstryデータの表示を変更
- GRRM23でのカッコ内のエネルギー値の取得とプロット機能の追加

#### 2024/1/13
- GRRM23にある程度対応。

### 1.2. 外部ビューワの設定

config.py をテキストエディタで開いて、下記の部分を利用する外部ビューワの絶対パスに書き換えてください。これは結果の構造を表示するビューワで、Jmolを想定しています。

```
VIEWER_PATH = 'D:/programs/jmol/jmol.bat'
```

内部的には下記のようなコマンドを実行して表示するので、それができるようにしておく必要があります。

```
VIEWER_PATH file.xyz
```

Windows+Jmolなら、Jmolのインストール先にある jmol.bat を開いて、JMOL_HOME を下記のように自身のディレクトリパスにしておき、それをVIEWER_PATHにしておくとよいです。

```
set JMOL_HOME="D:\programs\jmol"
```

### 1.3. 動作テスト環境

最新の動作テストは下記の環境でおこなっています。各種ライブラリのバージョンはわかりません。matplotlibは古いと動作が違うかもしれません。
- Windows 11 Pro
- Python 3.12
- numpy==2.1.2 
- wxPython==4.2.2
- matplotlib==3.9.2


## 2. 利用方法

grrm_single_viewer.pyw を実行して、メニューからファイルを開くか、表示されたウィンドウに読みたいログファイルをドロップしてください。このとき、同じディレクトリにcomファイルがあれば、それも読み込まれます。計算途中のジョブもだいたい読めるはずですが、FREQが中途半端だと動作がおかしいかもです。

ログが解析されて左上にログの中の計算内容（OPT/FREQ/IRC）が表示されます。SADDLEもMINもOPTとして認識されます。MIN+Eigencheck、SADDLE+IRCなどの複合ジョブの場合は、それぞれがログに書いてある順に表示されます。後は読みたい項目をダブルクリックすると、右上にその内容が表示されます。一番上のログファイル名をダブルクリックすると、（comファイルがあれば）計算条件とnormal terminationかどうか、などが表示されます。

### 2.1. OPT (MIN/SADDLE)

左側に各ステップのエネルギーや収束条件等がテーブルで表示できます。

テーブルの下のボタンは、下記の動作です。

- view : 選択中のステップの構造を表示
- coord : 選択中のステップのXYZ座標のテキストを表示
- plot : 構造最適化中のエネルギーや収束条件の変化をグラフ表示
- trajectory : 構造最適化全体を連続したxyzファイルで外部ビューワで表示

右側には、OPTジョブの終了状態と、最終エネルギー等が表示され、その構造（view）や座標 (coord)を表示できます（ログの Optimized structure 以下に対応）。
E1やE2はログのエネルギーの右側に表示されている2つの数値です（GRRM23のみ?）。これはジョブによって意味が異なるようですが、AFIRの場合はAFIR分のエネルギーを引いた真のエネルギーで、MECP探索系のジョブの場合は2つの電子状態のそれぞれのエネルギーのようです。


### 2.2. FREQ

左側に振動一覧が表示されます。viewボタンを押すと、その振動モードの簡易的な可視化アニメーション用のxyzファイルを外部ビューワで開きます。アニメーションの調整はStepとShiftで設定できます。

- Step : 何枚のxyzで表示するか（実際はこの4倍の枚数で1ループ）
- Shift : 一番変位の大きい原子を基準に何オングストローム動かすか。

右側には最後に出力される熱力学値が表示されます。
複数ある場合は上部から切り替えられます（quasi-RRHO処理が違う複数の値が表示されることがあります）。デフォルトでは最後のものがテーブルに表示されます。

### 2.3. IRC

一番上のplotでは、IRCの最後に表示される反応座標/エネルギーのグラフを表示します。これはジョブが終了していないと表示できません。
plot (reversed) は逆向きになります（x軸の反応座標の符号を反転）。

その下の trajectory は全体の反応パスを外部ビューワで表示します。forwardおよびbackwardの両方の計算がされていないと表示できません。
forward (逆向き) > TS > backward の順番、またはその逆の順番につなげて結果を可視化します。

その下のボックスで表示する方向（forward/backward）を指定します。片方しかないときは片方だけです。

Mode はIRC計算のタイプで、通常のIRCだとIRCとなります。鞍点以外のところから行った場合や、初期のHessian計算をしなかった場合（IRC計算単独で実行かつDownFC=-1の場合など）は、特殊なIRC計算になります。

その下のテーブルには各ステップのエネルギーが表示されます。その下のボタンはOPTと同じです。ここでのplotの横軸は反応座標ではなく、単にステップ数なので、一番上のplotとは少し違います。

またGRRMでは、特に指定しないとIRCの終点構造からMIN+FREQが実行されますが、その結果は左側のツリーのIRCの内部に表示されます。これをダブルクリックすれば通常のFREQ計算などと同じように表示されます。IRC計算時に初期にFREQ計算をしている場合、それもinitial/FREQとして表示されます（特に普段は読む必要はないでしょうけど）。

### 2.4. MIN+AFIR

AFIR条件でのMINのログ（やMC-AFIRの*_EQn.log）を読み込んだ場合、はMINに関しては普通にOPTとして表示されます。ここに表示されるエネルギーは、かけた力も含んだ見かけのPESのものです。計算終了後にログの最後に力を除いたエネルギープロファイルやapproximate EQ/TSが出力されますが、それはツリーのAFIR Pathをダブルクリックすると解析できます。

画面左側のボタンでエネルギープロファイルを表示します。対応するステップの構造や情報はOPTの方から見てください。

- plot (step) : 横軸にステップ数、縦軸にエネルギーのグラフを表示
- plot (lenght) : 横軸にlength、縦軸にエネルギーのグラフを表示。各点には対応するステップ数も表示。
- data (text) : ログの該当部分をテキスト表示

画面右側には、Approximate TS/EQ とエネルギーの一覧が表示されます。
一覧から選択してviewで構造、coordでそのxyz座標が表示できます。

### 2.5. LUP

LUP計算およびそれに続くSADDLEやIRC等を読み込むことができます（テスト中）。LUPのログを読み込むとLUPジョブの下に、（おこなわれていれば）SADDLE (OPT) やIRCのジョブが表示されます。


LUPをダブルクリックすると、LUPの最適化とApproximate TS/EQ構造のリストが表示されます。plotはAFIR Pathと同じく、最後に出力されるProfile部分のデータがプロットされます。
trajectoryを押すと連続したxyz形式ファイルが外部ビューワで表示されます。個々のNODEの構造を見たいときや座標データがほしいときは、ノード番号を入れてviewかcoordを押してください。

なお LUPは全NODEの計算が終わっているITRまでしか読み込みません。

## 3. 設定

一部の設定は config.py を書き換えて変更できます。
ほとんどは画面やテーブルの大きさに関する設定です。APP_PATH以外はあまり書き換えることはないかと思います。

## 4. デバッグ

手元にそんなに多様なパターンのログがなくて、ちゃんとデバッグできてないので、慎重に利用してください。適宜ログファイルをテキストエディタで見ながら確認して、表示がおかしくないことをチェックしたほうがよいです。（特に論文データ用のエネルギー値などは）

表示や構造がなにかおかしいと持ったら教えて下さい。
