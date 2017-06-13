$.extend({
    //x,y 坐标,radius 半径,process 百分比,backColor 中心颜色, proColor 进度颜色, fontColor 中心文字颜色,id
        DrowProcess:function(options) {
            var x=options.x|| 50;
            var y=options.y|| 50;
            var radius = options.radius ||50;
            var process = options.progress||0;
            var backColor = options.backColor || 'rgb(230, 230, 230)';
            var proColor = options.proColor || 'rgb(52, 145, 204)';
            var fontColor = options.fontColor || 'black';
            var fontScale = options.fontScale || 9; //字体大小
            var textdisplay=options.textdisplay==undefined?true:options.textdisplay;//文字显示
            var dirction=options.dirction==undefined?true:options.dirction;//时钟转动方向
            $("#"+options.id).text(options.progress);
            var canvas =$("#"+options.id)[0];
            if (canvas.getContext) {
                var cts = canvas.getContext('2d');
            } else {
                return;
            }
            cts.beginPath();
            // 坐标移动到圆心
            cts.moveTo(x, y);
            // 画圆,圆心是24,24,半径24,从角度0开始,画到2PI结束,最后一个参数是方向顺时针还是逆时针
            cts.arc(x, y, radius, 0,Math.PI*2, false);
            cts.closePath();
            // 填充颜色
            cts.fillStyle = backColor;
            cts.fill();

            cts.beginPath();
            // 画扇形的时候这步很重要,画笔不在圆心画出来的不是扇形
            cts.moveTo(x, y);
            // 跟上面的圆唯一的区别在这里,不画满圆,画个扇形
            //顺时针
            if(dirction){
                cts.arc(x, y, radius, Math.PI * 1.5,Math.PI * 2 * process / 100-Math.PI * 0.5 , false);
            }  //逆时针
            else{
                cts.arc(x, y, radius, Math.PI * 1.5, Math.PI * 1.5 - Math.PI * 2 * process / 100, true);
            }

            cts.closePath();
            cts.fillStyle = proColor;
            cts.fill();

            //填充背景白色
            cts.beginPath();
            cts.moveTo(x, y);
            cts.arc(x, y, radius - (radius * (options.circle||0.26)), 0, Math.PI * 2, true);
            cts.closePath();
            cts.fillStyle = 'rgba(255,255,255,1)';
            cts.fill();

            // 画一条线
            cts.beginPath();
            cts.arc(x, y, radius - (radius * ((options.circle+0.02)||0.3)),0, Math.PI * 2, true);
            cts.closePath();
            // 与画实心圆的区别,fill是填充,stroke是画线
            cts.strokeStyle = backColor;
            cts.stroke();

            //在中间写字
            cts.font =fontScale+"pt"+" Arial";
            cts.fillStyle = fontColor;
            cts.textAlign = 'center';
            cts.textBaseline = 'middle';
            cts.moveTo(x, y);
            if(textdisplay)
            {
                cts.fillText(process + "%", x, y);
            }
    },

        progress:function(options){
            var width =options.width||200;//画布宽度
            var height =options.height||200;//画布高度
            var outercanvas = '<canvas width='+width+' height='+height +'></canvas>';
            $("body").prepend(outercanvas);
            $("canvas:eq(0)").attr("id",options.id);
            var count = 0;
            var processcount = setInterval(function () {
            if (count >= (options.process||20)) {
                clearInterval(processcount);
            }
            options.progress=count;
            $.DrowProcess(options);
                count += 1;

        },options.time||100);

    },
    cicleprogressmore:function(options)
    {
        for(var items in options)
            $.progress(options[items]);
    }

})