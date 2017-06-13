//自定义验证
jQuery.validator.addMethod("telphone", function (value, element) {
    var tel = /^(0|86|17951)?(13[0-9]|15[012356789]|17[678]|18[0-9]|14[57])[0-9]{8}$/;
    return tel.test(value) || this.optional(element);
}, "请输入正确的手机号码");

jQuery.validator.addMethod("zipCode", function (value, element) {
    var tel = /^\d{6}$/;
    return tel.test(value) || this.optional(element);
}, "请输入正确的邮编");

jQuery.validator.addMethod("areaCode", function (value, element) {
    var areaCode = /^(0\d{2,3})$/;
    return areaCode.test(value) || this.optional(element);
}, "请输入正确的区号");

jQuery.validator.addMethod("card", function (value, element) {
    var card = /^\D\d{7}$|\d{8}$/;
    return card.test(value) || this.optional(element);
}, "请输入正确的卡号");

jQuery.validator.addMethod("phoneExt", function (value, element) {
    var phoneExt = /^(\d{4}|\d{3}|\d{2}|\d{1})$/;
    return phoneExt.test(value) || this.optional(element);
}, "请输入正确的分机号");

jQuery.validator.addMethod("phone", function (value, element) {
    var tel = /^(\(\d{3}\)|\d{3}-)?\d{8}|((\(\d{4}\)|\d{4}-)?\d{7})$/;
    return tel.test(value) || this.optional(element);
}, "请输入正确的电话号码");

jQuery.validator.addMethod("decimal", function (value, element) {
    var tel = /^\d+(\.\d+)?$/;
    return tel.test(value) || this.optional(element);
}, "请输入正确的小数");

jQuery.validator.addMethod("nonnegativeinteger", function (value, element) {
    var num = /^[0-9]+$/;
    return num.test(value) || this.optional(element);
}, "请输入非负整数");

jQuery.validator.addMethod("nonnegativeinteger", function (value, element) {
    var num = /^[0-9]+$/;
    return num.test(value) || this.optional(element);
}, "请输入非负整数");

jQuery.validator.addMethod("email", function (value, element) {
    var email = /\w+([-+.]\w+)*@\w+([-.]\w+)*\.\w+([-.]\w+)*/;
    return email.test(value) || this.optional(element);
}, "请正确输入邮箱");

jQuery.validator.addMethod("IdentifyCard", function (value, element) {
    var identifyCard = /^(\d{15}$|^\d{18}$|^\d{17}(\d|X|x))$/;
    return identifyCard.test(value) || this.optional(element);
}, "请正确输入身份证号");

jQuery.validator.addMethod("Birthday", function (value, element) {
    var Birthday = /^(19|20)\d{2}-(0?\d|1[012])-(0?\d|[12]\d|3[01])$/;
    return Birthday.test(value) || this.optional(element);
}, "请正确输入生日");

jQuery.validator.addMethod("named", function (value, element) {
    var named =/^[a-z]+[a-zA-Z0-9_]*$/;
    return named.test(value) || this.optional(element);
}, "镜像名称只能包含字母、数字、下划线，且以字母开头");