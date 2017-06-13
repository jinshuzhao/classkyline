var TITEMS = [
 ["H3C云学堂管理平台帮助文档", "html/sysIntro.html", "1",
  ["系统简介", "html/welcomesysIntro.html", "11"],
  ["云主机监控", "html/HostMonitor.html", "11"],
  ["镜像管理", "html/ImageMgmt.html", "11"],
  ["课程管理", "html/ClassTemple.html", "11"],
  ["云桌面管理", "html/desktopMgmt.html", "11"],
  ["账户管理", "html/UserMgmt.html", "11"],
  ["网络管理", "html/NetworkMgmt.html", "11"],
  ["系统管理", "html/SystemMgmt.html", "1",
   ["系统设置", "html/SystemMgmt/SystemSet.html", "11"],
   ["日志下载", "html/SystemMgmt/LogDownload.html", "11"],
   ["系统升级", "html/SystemMgmt/Upgrade.html", "11"],
   ["License管理", "html/SystemMgmt/LicenseMgmt.html", "1",
    ["查看License详细信息", "html/SystemMgmt/LicenseMgmt/LicenseDetail.html", "11"],
    ["正式申请License", "html/SystemMgmt/LicenseMgmt/RequestLicense.html", "11"],
    ["注册License", "html/SystemMgmt/LicenseMgmt/RegisterLicense.html", "11"],
   ]
  ],
  ["典型应用", "html/MgmtDeploy.html", "11"],
 ]
];


var FITEMS = arr_flatten(TITEMS);

function arr_flatten (x) {
   var y = []; if (x == null) return y;
   for (var i=0; i<x.length; i++) {
       if (typeof(x[i]) == "object") {
           var flat = arr_flatten(x[i]);
           for (var j = 0; j < flat.length; j++)
               y[y.length] = flat[j];
       } else {
           if ((i % 3 == 0))
               y[y.length] = x[i + 1];
       }
   }
   return y;
}
