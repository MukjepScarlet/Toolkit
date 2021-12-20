import time
import datetime
from win10toast import ToastNotifier
from selenium import webdriver


"""
Notifications
"""
toaster = ToastNotifier()


"""
签到
"""

"""
检测时间是否在签到有效时间范围内
"""
now = datetime.now()
begin = datetime.strptime(str(now.date()) + '5:00', r'%Y-%m-%d%H:%M')
end = datetime.strptime(str(now.date()) + '19:30', r'%Y-%m-%d%H:%M')
if now < begin or now >= end:
    toaster.show_toast("Error", "现在不能签到!")
    exit(0)

"""
用户输入账号密码
"""
auth = ""
password = ""


opt = webdriver.ChromeOptions()
opt.headless = True
driver = webdriver.Chrome(options = opt)


driver.get("https://ids.xmu.edu.cn/authserver/login?service=https://xmuxg.xmu.edu.cn/login/cas/xmu")

driver.find_element_by_id("username").send_keys(auth)
driver.find_element_by_id("password").send_keys(password)
# TODO: 考虑验证码以及登录失败的情况
driver.find_element_by_xpath("//button[@type='submit']").click()#登录, 也可以在输入密码时加一个\n
time.sleep(1)

#Switch to target page
driver.get("https://xmuxg.xmu.edu.cn/app/214")
time.sleep(2)
driver.find_element_by_xpath("//div[@title='我的表单']").click()
time.sleep(2)
if "是" in driver.find_element_by_xpath("//div[@data-name='select_1582538939790']").text:
    toaster.show_toast("Info", "你今天已经打卡.")
else:
    driver.find_element_by_xpath("//div[@data-name='select_1582538939790']").click()
    time.sleep(1)
    driver.find_element_by_xpath("//label[@title='是 Yes']").click()
    time.sleep(1)
    driver.find_element_by_xpath("//i[@disabled='disabled' and @class='maticon']").click()
    time.sleep(1)
    alert = driver.switch_to.alert
    alert.accept()
    time.sleep(1)
    driver.get("https://xmuxg.xmu.edu.cn/app/214")
    time.sleep(1)
    driver.find_element_by_xpath("//div[@title='我的表单']").click()

time.sleep(1)

latest_time = driver.find_element_by_xpath("//div[@class='v-datepicker info-value btn-block with-reset-button']").text.split('\n')[0]
latest_time_d = datetime.strptime(latest_time, r'%Y-%m-%d %H:%M:%S')
if latest_time_d >= begin and latest_time_d < end:
    toaster.show_toast("Info", "你今天已经打卡.")

toaster.show_toast("Info", f"最后一次打卡时间: {latest_time}")

driver.close()
