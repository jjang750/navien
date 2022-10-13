# 경동 나비엔 보일러 Home Assistant Climate

1) 테스트 시스템 사양<br>
  - 경동 나비엔 NR-40D 룸 콘트롤러<br>
  - 나비엔 스마트톡 <br>
  - SmartThings App<br>

2) 사전 준비 사항 
  - 룸 콘트롤러와 나비엔 스마트톡 연동 필수
  - 나비엔 스마트톡 > 설정 >  연동형 부가서비스 > SmartThings 체크
  
  ※ 룸 콘트롤러 마다 연동형 부가서비스가 지원 안되는 경우가 있습니다. 연동형 부가서비스가 없다면 경동 고객센터에 문의하세요.
  
  ※ SmartThings API를 사용하기 때문에 나비엔 스마트톡과 SMartThings의 연동형 부가서비스가 필수입니다.

3) SmartThings 앱에서 상단의 기기추가 버튼을 눌러 Navien 기기를 추가 해줍니다. 
  - 기기 추가 시 나비엔 스마트톡 아이디와 패스워드가 필요합니다.
  
4) SmartThings API 접근을 위한 엑세스 토큰 발급이 필요합니다.<br>
  참조 : https://cafe.naver.com/koreassistant/10624
  
5) 나비엔 롬 콘트롤러와 연결 된 기기의 device id를 찾기 위해 SmartThings API 접속합니다.
  - URL : https://graph-ap02-apnortheast2.api.smartthings.com/location/list<br>
          ※ SmartThings API에 가입 시 입력한 아이디와 패스워드가 필요합니다.
  - 로그인 후 상단 메뉴의 "My Devices" 메뉴를 클릭하여 SmartThings에 등록 된 기기 목록을 조회합니다.
  - 조회 된 목록 중 "나비엔 보일러	Navien Room Controller" 가 보인다면 제대로 연결이 된 것이고<br> 
    만약, 나비에 보일러가 보이지 않는다면 처음부터 빼 놓은 부분이 있는지 확인 후 다시 설정이 필요합니다.

6) My Devices 목록에서 나비엔 보일러를 클릭하여 상세페이지로 이동합니다.
  - 상세페이지의  URL에 기기의 device id가 조회 됩니다.
  - device id는 이후에 이벤트 데이터 조회를 위해 필요합니다.
  - 예) https://graph-ap02-apnortheast2.api.smartthings.com/device/show/<b>c9fbd5c5-63ab-4e9c-9d7d-5c72b599a847</b>
  - 링크 show/ 뒤에 굵은 색 부분이 device id 입니다.
  
7) 이제 나비엔 climate에 접속하기 위한 사전 준비가 끝났습니다.
  - 필수사항 : <br> 
     SmartThings API token<br>
     나비엔 보일러 device id

8) 이제 homeassistant/custom_components 폴더 밑에 navien_boiler를 만들고 그 안에
  프로그램을 다운 받습니다.
  - sensor.py <- sensor 
  - manifest.json <- 기본정보
  - commands.json <- SmartThings API 명령어
  - climate.py <- Climate
  - \_\_init__.py

9) 파일 중 commands.json을 열어 token값과 deviceId값을 수정합니다.
  - "token": "<b>a81c7152-87a0-4f2f-877b-19f4b20XXXXX</b>"
  - "deviceId": "<b>c9fbd5c5-63ab-4e9c-9d7d-5c72b59XXXXX</b>"
  - "긁은 색으로 표시 된 부분만 수정해야 합니다."


10) homeassistant/configuration.yaml 에 climate 를 추가합니다.

climate:
  - platform: navien_boiler
    scan_interval: 360

sensor:
  - platform: navien_boiler
    scan_interval: 360

11) Home Assistant를 재시작 하면 적용됩니다.



