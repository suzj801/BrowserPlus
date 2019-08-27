# BrowserPlus
New browser written by PyQt5

# 待完成功能
1. 配置保存
2. Plugins
3. 任务推送

# Trouble
考虑到跨平台、部署简化、目录打包，目前只采用sqlite来做配置/数据存取
webenginepage不再使用NetworkAccessManager, 所以目前无法抓取网页提交数据
cookie都存在数据里, requests请求之前可以从数据库里获取cookie以达到登录等效果, 但目前数据库里的cookie没有过期时间