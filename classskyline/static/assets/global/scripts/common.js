var minute = 1000 * 60;
var hour = minute * 60;
var day = hour * 24;
var halfamonth = day * 15;
var month = day * 30;
var spinner;
function loading() {
    $('.bg').fadeIn(1000);
    var opts = {
            lines: 13, // 花瓣数目
            length: 20, // 花瓣长度
            width: 10, // 花瓣宽度
            radius: 30, // 花瓣距中心半径
            corners: 1, // 花瓣圆滑度 (0-1)
            rotate: 0, // 花瓣旋转角度
            direction: 1, // 花瓣旋转方向 1: 顺时针, -1: 逆时针
            color: '#5882FA', // 花瓣颜色
            speed: 1, // 花瓣旋转速度
            trail: 60, // 花瓣旋转时的拖影(百分比)
            shadow: false, // 花瓣是否显示阴影
            hwaccel: false, //spinner 是否启用硬件加速及高速旋转
            className: 'spinner', // spinner css 样式名称
            zIndex: 2e9, // spinner的z轴 (默认是2000000000)
            top: '50%', // spinner 相对父容器Top定位 单位 px
            left: '50%'// spinner 相对父容器Left定位 单位 px
        };
    var target = document.getElementById('mainload');
    spinner = new Spinner(opts).spin(target);
}

function reload_page() {
    window.location.reload();
}

var common = {
    //页面进度条
    loadprogress:function(){
          var mask='<div class="mask"></div>';
          $("body").prepend(mask);
          $(".mask").css({
              "width":"100%",
              "height":"100%",
              "position":"absolute",
              "left":0,
              "top":0,
              "background-color":"#333",
              "opacity":0.5,
              "z-index":20000
          });
          $.progress({
              x:150,
              y:150,
              radius:100,
              process:100,
              backColor:'#ccc',
              proColor:'#2374c6',
              fontColor:'#000',
              fontScale:12,
              id:'canvas01',
              width:400,
              height:400,
              time:100,
              circle:0.33, //最大数值到1
              textdisplay:true,
              dirction:false //逆时针false,默认顺时针
          });
    },
    destoryprogress:function(){
        $("#canvas01").remove();
        $(".mask").remove();
    },
    //左侧的导航菜单有二级或三级菜单时才会触发到该事件
    initmenu: function (parentmenu, submenu) {
        $("." + parentmenu).parent().find("li").removeClass("active");
        $("." + parentmenu).addClass("active").children().find("arrow").addClass("open");
        if (submenu.length > 0) {
            $("." + submenu).addClass("active");

        }
    },
    initmenu2: function (parentmenu, submenu, sub2menu) {
        $("." + parentmenu).parent().find("li").removeClass("active");
        $("." + parentmenu).addClass("active").children().find("arrow").addClass("open");
        if (submenu.length > 0) {
            $("." + submenu).addClass("active");
        }

        if (sub2menu.length > 0) {
            $("." + sub2menu).addClass("active");
        }
    },
    newguid: function () {
        //guid(全局唯一标识符)生成函数

        var guid = "";
        for (var i = 1; i <= 32; i++) {
            var n = Math.floor(Math.random() * 16.0).toString(16);
            guid += n;
            if ((i == 8) || (i == 12) || (i == 16) || (i == 20))
                guid += "-";
        }
        return guid;

    },
    ajaxgetrequest:function(option,suc,err){
         $.ajax({
            type: 'get',
            dataType: 'json',
            url: option.url,
            async: option.async,
             data:option.data,//如果有id，默认给与null值。
            beforeSend: function () {
                    //异步请求时spinner出现
                //loading();
                },
            success: suc,
            complete:function(){
                //spinner.spin();
                //$(".bg").fadeOut(200);
            },
            error:err
        });
    },
    ajaxpostrequest: function (option, suc) {
        $.ajax({
            type: 'post',
            dataType: 'json',
            url: option.url,
            async: option.async,
            data: option.data,
            //beforeSend: function () {
            //        //异步请求时spinner出现
            //    loading();
            //
            //    },
            success: suc,
            //complete:function(){
            //    spinner.spin();
            //    $(".bg").fadeOut(200);
            //},
            error: function(){
                if (spinner) {
                    spinner.stop();
                    $(".bg").fadeOut(2000);
                    notie.alert(3, "服务器错误,请稍候重试!", 3);
                }

            }
        });
    },
    //全选或者全不选
    checkall: function (classname, dom) {
        var checked = $(dom).attr("checked");
        if (checked == null || checked == undefined) {
            $("." + classname).each(function() {
                $(this).attr("checked", false);
            });
        } else {
            $("." + classname).each(function () {
                $(this).attr("checked", checked);
            });
        }
       
    },
    checkallparent: function (classname,dom) {
        var checked = $(dom).attr("checked");
        if (checked == null || checked == undefined) {
            $("." + classname).each(function () {
                var span = $(this).parent();
               
                    span.removeClass("checked");
               
            });
        }
        else {
            $("." + classname).each(function () {
                var span = $(this).parent();

                span.addClass("checked");

            });
        }
    },
    //取通过url传过来的值
    Request: function (paras) {
        var url = location.href;
        var paraString = url.substring(url.indexOf("?") + 1, url.length).split("&");
        var paraObj = {}
        for (i = 0; j = paraString[i]; i++) {
            paraObj[j.substring(0, j.indexOf("=")).toLowerCase()] = j.substring(j.indexOf("=") + 1, j.length);
        }
        var returnValue = paraObj[paras.toLowerCase()];
        if (typeof (returnValue) == "undefined") {
            return "";
        } else {
            return returnValue;
        }
    },
    //提示弹窗
    alert: function () {//需要引用jqueryui及相应的css文件才能使用。
        // info dialog
        $("#alertinfo").dialog({
            dialogClass: 'ui-dialog-blue',
            autoOpen: false,
            resizable: false,
            height: 250,
            modal: true,
            buttons: [
              {
                  "text": "OK",
                  'class': 'btn green',
                  click: function () {
                      $(this).dialog("close");
                  }
              }
            ]
        });
    },
    confirm: function () {
        //confirm dialog
        $("#confirminfo").dialog({
            dialogClass: 'ui-dialog-green',
            autoOpen: false,
            resizable: false,
            height: 210,
            modal: true,
            buttons: [
              {
                  'class': 'btn red',
                  "text": "Delete",
                  click: function () {
                      $(this).dialog("close");
                  }
              },
              {
                  'class': 'btn',
                  "text": "Cancel",
                  click: function () {
                      $(this).dialog("close");
                  }
              }
            ]
        });
    },
    timeago: function (dateTimeStamp) {
        var now = new Date().getTime();
        var diffValue = now - dateTimeStamp;
        if (diffValue < 0) {
            //若日期不符则弹出窗口告之
            //alert("结束日期不能小于开始日期！");
        }
        var monthC = diffValue / month;
        var weekC = diffValue / (7 * day);
        var dayC = diffValue / day;
        var hourC = diffValue / hour;
        var minC = diffValue / minute;
        var result = "";
        if (monthC >= 1) {
            result = "" + parseInt(monthC) + "个月前";
        }

        else if (weekC >= 1) {
            result = "" + parseInt(weekC) + "周前";
        }
        else if (dayC >= 1) {
            result = "" + parseInt(dayC) + "天前";
        }
        else if (hourC >= 1) {
            result = "" + parseInt(hourC) + "小时前";
        }
        else if (minC >= 1) {
            result = "" + parseInt(minC) + "分钟前";
        } else
            result = "刚刚";
        return result;
    },
    totimestamp: function (dateStr) {
        return Date.parse(dateStr.replace(/-/gi, "/"));
    },

    initArea: function(){
        $.ajax({
            type:"GET",
            url:"/h3cloud/getSession",
            data:{"key":"area_name"}, 
            datatype: "text",                          
            success:function(data){
                 $("#area_name").text(data); 
            }
        })
    },

    // 刷新页面
    reload_page: function() {
        setTimeout(reload_page, 1000);
    }
};
/*   
函数：格式化日期   
参数：formatStr-格式化字符串   
d：将日显示为不带前导零的数字，如1   
dd：将日显示为带前导零的数字，如01   
ddd：将日显示为缩写形式，如Sun   
dddd：将日显示为全名，如Sunday   
M：将月份显示为不带前导零的数字，如一月显示为1   
MM：将月份显示为带前导零的数字，如01  
MMM：将月份显示为缩写形式，如Jan  
MMMM：将月份显示为完整月份名，如January  
yy：以两位数字格式显示年份  
yyyy：以四位数字格式显示年份  
h：使用12小时制将小时显示为不带前导零的数字，注意||的用法  
hh：使用12小时制将小时显示为带前导零的数字  
H：使用24小时制将小时显示为不带前导零的数字  
HH：使用24小时制将小时显示为带前导零的数字  
m：将分钟显示为不带前导零的数字  
mm：将分钟显示为带前导零的数字  
s：将秒显示为不带前导零的数字  
ss：将秒显示为带前导零的数字  
l：将毫秒显示为不带前导零的数字  
ll：将毫秒显示为带前导零的数字  
tt：显示am/pm  
TT：显示AM/PM  
返回：格式化后的日期  
*/
Date.prototype.format = function (formatStr) {
    var date = this;
    /*  
	函数：填充0字符  
	参数：value-需要填充的字符串, length-总长度  
	返回：填充后的字符串  
	*/
    var zeroize = function (value, length) {
        if (!length) {
            length = 2;
        }
        value = new String(value);
        for (var i = 0, zeros = ''; i < (length - value.length) ; i++) {
            zeros += '0';
        }
        return zeros + value;
    };
    return formatStr.replace(/"[^"]*"|'[^']*'|\b(?:d{1,4}|M{1,4}|yy(?:yy)?|([hHmstT])\1?|[lLZ])\b/g, function ($0) {
        switch ($0) {
            case 'd': return date.getDate();
            case 'dd': return zeroize(date.getDate());
            case 'ddd': return ['Sun', 'Mon', 'Tue', 'Wed', 'Thr', 'Fri', 'Sat'][date.getDay()];
            case 'dddd': return ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday'][date.getDay()];
            case 'M': return date.getMonth() + 1;
            case 'MM': return zeroize(date.getMonth() + 1);
            case 'MMM': return ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'][date.getMonth()];
            case 'MMMM': return ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December'][date.getMonth()];
            case 'yy': return new String(date.getFullYear()).substr(2);
            case 'yyyy': return date.getFullYear();
            case 'h': return date.getHours() % 12 || 12;
            case 'hh': return zeroize(date.getHours() % 12 || 12);
            case 'H': return date.getHours();
            case 'HH': return zeroize(date.getHours());
            case 'm': return date.getMinutes();
            case 'mm': return zeroize(date.getMinutes());
            case 's': return date.getSeconds();
            case 'ss': return zeroize(date.getSeconds());
            case 'l': return date.getMilliseconds();
            case 'll': return zeroize(date.getMilliseconds());
            case 'tt': return date.getHours() < 12 ? 'am' : 'pm';
            case 'TT': return date.getHours() < 12 ? 'AM' : 'PM';
        }
    });
}