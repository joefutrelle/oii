(function($) {
    $.fn.extend({
       closeBox: function() {
           return this.each(function () {
               var $this = $(this); // retain ref to $(this)
               $this.prepend('<a class="close"></a>').find('a:first')
                   .css('cursor','pointer')
                   .bind('click', function() {
                       $this.css('display','none');
                   });
           });// each in closeBox
       }//closeBox
    });//$.fn.extend
})(jQuery);//end of plugin
