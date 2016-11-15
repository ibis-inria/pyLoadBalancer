var rem = function rem() {
   var html = document.getElementsByTagName('html')[0];

   return function () {
       return parseInt(window.getComputedStyle(html)['fontSize']);
   }
}();
const COLORS =  ['rgb(55,126,184)','rgb(77,175,74)','rgb(228,26,28)','rgb(255,127,0)','rgb(152,78,163)','rgb(166,86,40)','rgb(247,129,191)','rgb(214,214,0)','rgb(153,153,153)']
const TRANSPCOLORS =  ['rgba(55,126,184,0.6)','rgba(77,175,74,0.6)','rgba(228,26,28,0.6)','rgba(255,127,0,0.6)','rgba(152,78,163,0.6)','rgba(166,86,40,0.6)','rgba(247,129,191,0.6)','rgba(214,214,0,0.6)','rgba(153,153,153,0.6)']
const VERYTRANSPCOLORS =  ['rgba(55,126,184,0.3)','rgba(77,175,74,0.3)','rgba(228,26,28,0.3)','rgba(255,127,0,0.3)','rgba(152,78,163,0.3)','rgba(166,86,40,0.3)','rgba(247,129,191,0.3)','rgba(214,214,0,0.3)','rgba(153,153,153,0.3)']
