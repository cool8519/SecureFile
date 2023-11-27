SecureFile
=============================
파일 업로드/다운로드를 위한 프로그램이다.
일반적으로 이를 위해서는 ftpd와 같은 서버 모듈과 ftp client 프로그램이 필요하다.
이 프로그램은 웹서버의 UI가 client로 동작하고, python 모듈이 server로 동작하며, websocket을 통신 프로토콜로 사용한다.
wss를 통해 보안을 보장하며, 웹서버 포트만 개방하면 사용이 가능하다.

Requirements
---------------
* Web Server
* Python 3 (3.6 이상에서 테스트 됨)

Getting Started
---------------
1. Backend Server 구성

 - PIP를 이용하여 tornado 모듈을 설치한다.
   > python -m pip install tornado
 - 임의의 위치에 SecureFile 파일들을 복사한다.
 - WebSocketServer.py를 실행한다. 인자값으로 포트 번호를 줄 수 있다.(기본 포트: 8008)
   > python WebSocketServer.py<br>
   > 또는<br>
   > python WebSocketServer.py 8080

2. Web Server 구성
 - 웹서버를 설치한다. Apache HTTP Server, Nginx 등을 사용할 수 있다.
 - SecureFile 웹화면에서 사용할 도메인명과 포트로 vhost를 구성을 한다. (config 디렉토리 하위 파일 참고)
 - 임의의 위치에 SecureFile의 static 하위 파일들을 복사한다. Backend Server와 동일할 경우, 별도 복사가 필요없다.
 - /securefile/ws/ URL을 기동한 Python Backend Server로 Proxy 되도록 설정한다.
   ```
   # nginx vhost 설정 예시(SecureFile 단독구성)
   
   server {
     listen      80;
     listen      443 ssl;
     server_name securefile.service-domain.com;

	 auth_basic "Restricted Access.";
	 auth_basic_user_file /etc/nginx/.htpasswd;

     index    index.html  index.htm;

     location /securefile {
       alias "/mydir/SecureFile/static/";
     }
     location /securefile/ws/ {
       proxy_http_version 1.1;
       proxy_set_header Upgrade $http_upgrade;
       proxy_set_header Connection "upgrade";
       proxy_set_header Host $host;
       proxy_pass http://127.0.0.1:8080/ws/;
     }
   ```
   
Usage
---------------
- 뤱브라우저로 "https://my-domain/securefile"로 접속
  인증창에 웹서버 구성시 설정한 ID/PW를 입력
- 디렉토리 이동  
  하위 또는 상위(..) 디렉토리 클릭
- 파일 다운로드, 삭제
  해당 파일 클릭
- 파일 업로드  
  1. Filename 박스 클릭 후 업로드 할 파일 선택    
     또는 파일을 Filename 박스로 Drag&Drop
  2. Upload 버튼 클릭
※ 웹브라우저가 없는 경우, 별도 제공 프로그램을 통해 터미널 환경에서 사용 가능(program/FileCommand.py)

Note
--------------
- 디렉토리 생성 및 삭제는 미지원
- 특정 디렉토리 하위는 보안상 접근 불가  
  Windows는 `C:\Windows` 하위 접근 제한, 기본 위치는 `%TEMP%` 환경변수에 정의된 위치 
  Unix(Linux)는 `/` 하위 접근 제한, 기본 위치는 `/tmp`    
  ※ handler/FileHandler.py 내 init_path 및 perm_path 수정을 통해 정책 변경 가능
- 보안을 위해 Client IP가 "127.0.0.1"인 경우만 허용
  웹서버가 Backend Server와 동일한 노드에 있지 않는 경우, WebSocketServer.py 내 allowed_ip_list 수정 필요
