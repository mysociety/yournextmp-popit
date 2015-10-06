$(function() {
  var toggleFullVersion = function toggleFullVersion($fullVersion){
    if($fullVersion.is(':visible')){
      $fullVersion.hide().siblings('.js-toggle-full-version-json').text(gettext('Show full version'));
    } else {
      $fullVersion.show().siblings('.js-toggle-full-version-json').text(gettext('Hide full version'));
    }
  }

  toggleFullVersion($('.full-version-json'));

  $('.js-toggle-full-version-json').on('click', function(){
    toggleFullVersion($(this).siblings('.full-version-json'));
  });
});
