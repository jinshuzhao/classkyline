/*************************************************************************
 chm2web Navigation Script 1.0 
 Copyright (c) 2002-2007 A!K Research Labs (http://www.aklabs.com)
 http://chm2web.aklabs.com - HTML Help Conversion Utility
**************************************************************************/

var NV = ["src/intro.htm","src/features.htm","src/about/versions.htm","src/sysreq.htm","src/work/work.htm","src/work/projects.htm","src/work/params.htm","src/work/convoptions/version.htm","src/work/convoptions/general.htm","src/work/convoptions/template.htm","src/work/convoptions/pageprep.htm","src/work/convoptions/ssheet.htm","src/work/templates.htm","src/work/globalvars.html","src/work/tmplbody.htm","src/work/body/body_info.html","src/work/body/open_fields.html","src/work/body/config_manager.html","src/work/body/noframes_version.html","src/work/body/frames_version.html","src/work/body/mobile_version.html","src/work/tmplscheme.htm","src/work/scheme/template_info.html","src/work/scheme/open_fields.html","src/work/scheme/copy_files.html","src/work/oldtemplate.htm","src/work/cmdline.htm","src/work/cmdext.htm","src/work/context.htm","src/work/decomp.htm","src/work/regexpr.htm","src/hoto/createhelp.htm","src/register/register.htm","src/register/license.htm","src/register/whyreg.htm","src/about/progupd.htm","src/about/techsup.htm","src/products.htm","src/about/contact.htm","src/about/copyright.htm"];
var s = "source/";
function getNav(op) { var p=chmtop.c2wtopf.pageid;var n=s+p; var m=NV.length-1;for(i=0;i<=m;i++){if(NV[i]==p){if(op=="next"){if (i<m) {curpage=i+1;return s+NV[i+1];} else return n;}else{if(i>0) {curpage=i-1;return s+NV[i-1];} else return n;}}} return n;}
function syncTopic(){open('helpheaderc.html', 'header');open('helpcontents.html','toc');}
