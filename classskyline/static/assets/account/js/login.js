
jQuery(document).ready(function () {
    $("#main").keydown(function (e) {
        var curKey = e.which;
        if (curKey == 13) {
            $("#btnmake").click();
            return false;
        }
    });
    //document.onkeydown = function(e){
    //    var isie = (document.all) ? true : false; 
    //    var key;
         
    //    if (isie) 
    //        key = window.event.keyCode; 
    //    else 
    //    { 
    //        key = e.which; 
    //    } 

    //    if(key==13) 
    //    {
    //        //alert(e.keyCode);
    //        $("#btnmake").click();
    //        e.keyCode = 0
    //        e.returnValue = false;
    //        return false;
    //    }
    //}

    $("#btnmake").click(function () {
        login();
    })

    $("#errorMeesage").text("");

    $("#btnsave").click(function () {
         $("#name").val("");
         $("#pwd").val("");
    })
});
 
function login() {
    $("#errorMeesage").text("");
    var name = $("#name").val();
    var pwd = $("#pwd").val();
    if (!check())
    {
        $("#errorMeesage").text("帐号错误");
        return;
    }
    url = '/account/check';
 
    $.ajax({
        url: url,
        data: { "name": name, "pwd":pwd},
        type: "POST",
        dataType: "json",
        success: function (data) {
      
            if(data.status=="success")
            {
                var href = window.location.href;
                if (href.indexOf("next") > 0)
                {
                    var next = href.substring(href.indexOf("next")+5);
                    window.location.href = next;
                }
                else 
                    window.location.href = "/cloudclass/"
            }
            else 
            {
                $("#errorMeesage").text("用户名或密码错误");
            }
        },
        error: function (data) {
             
            alert("系统异常");
        }
    });
}

function check()
{
    var name = $("#name").val();
    var pwd = $("#name").val();
    if (name.length <= 0)
        return false;
    if (pwd.length <= 0)
        return false;

    return true;
}