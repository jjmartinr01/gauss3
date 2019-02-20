/* ---------------------------------------------
Nested Accordion v.1.4.7.3
Script to create 'nestedaccordion' functionality on a hierarchically structured content.
http://www.adipalaz.com/experiments/jquery/nested_nestedaccordion.html
Requires: jQuery v1.4.2+
Copyright (c) 2009 Adriana Palazova
Dual licensed under the MIT (http://www.adipalaz.com/docs/mit-license.txt) and GPL (http://www.adipalaz.com/docs/gpl-license.txt) licenses.
------------------------------------------------ */
(function($) {
//$.fn.orphans - http://www.mail-archive.com/jquery-en@googlegroups.com/msg43851.html
$.fn.orphans = function(){
var txt = [];
this.each(function(){$.each(this.childNodes, function() {
  if (this.nodeType == 3 && $.trim(this.nodeValue)) txt.push(this)})}); return $(txt);};
  
$.fn.nestedaccordion = function(options) {
    var o = $.extend({}, $.fn.nestedaccordion.defaults, options);
    
    return this.each(function() {
      var containerID = o.container ? '#' + this.id : '', objID = o.objID ? o.objID : o.obj + o.objClass,
        Obj = o.container ? containerID + ' ' + objID : '#' + this.id,
        El = Obj + ' ' + o.el,
        hTimeout = null; 

      // build
      if (o.head) $(Obj).find(o.head).addClass('h');
      if (o.head) {
        if ($(El).next('div:not(.outer)').length) {$(El).next('div:not(.outer)').wrap('<div class="outer" />');} 
        $(Obj + ' .h').each(function(){
            var $this = $(this);
            if (o.wrapper == 'div' && !$this.parent('div.new').length) {$this.add( $this.next('div.outer') ).wrapAll('<div class="new"></div>');}
        }); 
      }
      $(El).each(function(){
          var $node = $(this);
          if ($node.find(o.next).length || $node.next(o.next).length) {
            if ($node.find('> a').length) {
                $node.find('> a').addClass("trigger").css('display', "block");
            } else {
                var anchor = '<a class="trigger" style="display:block" href="#" />'
                if (o.elToWrap) {
                  var $t = $node.orphans(), $s = $node.find(o.elToWrap);
                  $t.add($s).wrapAll(anchor);
                } else {
                  $node.orphans().wrap(anchor);
                }
            }
          } else {
            $node.addClass('last-child');
            if (o.lastChild && $node.find('> a').length) {$node.find('> a').addClass("trigger").css('display', "block");}
          }
      });
      // init state
      $(El + ' a.trigger').closest(o.wrapper).find('> ' + o.next).not('.shown').hide().closest(o.wrapper).find('a.open').removeClass('open').data('state', 0);
      if (o.activeLink) {
          var loc,
              fullURL = window.location.href,
              path = window.location.pathname.split( '/' ),
              page = path[path.length-1];
              (o.uri == 'full') ? loc = fullURL : loc = page;
          $(Obj + ' a:not([href $= "#"])[href$="' + loc + '"]').addClass('active').parent().attr('id', 'current').closest(o.obj).addClass('current');
          if (o.shift && $(Obj + ' a.active').closest(o.wrapper).prev(o.wrapper).length) {
            var $currentWrap = $(Obj + ' a.active').closest(o.wrapper),
                $curentStack = $currentWrap.nextAll().andSelf(),
                $siblings = $currentWrap.siblings(o.wrapper),
                $first = $siblings.filter(":first");
            if (o.shift == 'clicked' || (o.shift == 'all' && $siblings.length)) {
                $currentWrap.insertBefore($first).addClass('shown').siblings(o.wrapper).removeClass('shown');
            }
            if (o.shift == 'all' && $siblings.length > 1) {$curentStack.insertBefore($first);}
          }
      }
      if (o.initShow) {
        $(Obj).find(o.initShow).show().addClass('shown')
          .parents(Obj + ' ' + o.next).show().addClass('shown').end()
          .parents(o.wrapper).find('> a.trigger, > ' + o.el + ' a.trigger').addClass('open').data('state', 1);
          if (o.expandSub) {$(Obj + ' ' + o.initShow).children(o.next).show().end().find('> a').addClass('open').data('state', 1 );}
      }
      // event
      if (o.event == 'click') {
          var ev = 'click';
      } else  {
          if (o.focus) {var f = ' focus';} else {var f = '';}
          var ev = 'mouseenter' + f;
      }
      var scrollElem;
      (typeof scrollableElement == 'function') ? (scrollElem = scrollableElement('html', 'body')) : (scrollElem = 'html, body');

      // The event handler is bound to the "nestedaccordion" element
      // The event is filtered to only fire when an <a class="trigger"> was clicked on.
      $(Obj).delegate('a.trigger', ev, function(ev) {
          var $thislink = $(this),
              $thisWrapper = $thislink.closest(o.wrapper),
              $nextEl = $thisWrapper.find('> ' + o.next),
              $siblings = $thisWrapper.siblings(o.wrapper),
              $trigger = $(El + ' a.trigger'),
              $shownEl = $thisWrapper.siblings(o.wrapper).find('>' + o.next + ':visible'),
              shownElOffset;
              $shownEl.length ? shownElOffset = $shownEl.offset().top : shownElOffset = false;
              
          function action(obj) {
             if (($nextEl).length && $thislink.data('state') && (o.collapsible)) {
                  $thislink.removeClass('open');
                  $nextEl.filter(':visible')[o.hideMethod](o.hideSpeed, function() {$thislink.data('state', 0);});
              }
              if (($nextEl.length && !$thislink.data('state')) || (!($nextEl).length && $thislink.closest(o.wrapper).not('.shown'))) {
                  if (!o.standardExpansible) {
                    $siblings.find('> a.open, >'+ o.el + ' a.open').removeClass('open').data('state', 0).end()
                    .find('> ' + o.next + ':visible')[o.hideMethod](o.hideSpeed);
                    if (shownElOffset && shownElOffset < $(window).scrollTop()) {$(scrollElem).animate({scrollTop: shownElOffset}, o.scrollSpeed);}
                  }
                  $thislink.addClass('open');
                  $nextEl.filter(':hidden')[o.showMethod](o.showSpeed, function() {$thislink.data('state', 1);});
              }
              if (o.shift && $thisWrapper.prev(o.wrapper).length) {
                var $thisStack = $thisWrapper.nextAll().andSelf(),
                    $first = $siblings.filter(":first");
                if (o.shift == 'clicked' || (o.shift == 'all' && $siblings.length)) {
                  $thisWrapper.insertBefore($first).addClass('shown').siblings(o.wrapper).removeClass('shown');
                }
                if (o.shift == 'all' && $siblings.length > 1) {$thisStack.insertBefore($first);}
              }
          }
          if (o.event == 'click') {
              action($trigger); 
              if ($thislink.is('[href $= "#"]')) {
                  return false;
              } else {
                  if ($.isFunction(o.retFunc)) {
                    return o.retFunc($thislink) 
                  } else {
                    return true;
                  }
              }
          }
          if (o.event != 'click') {
              hTimeout = window.setTimeout(function() {
                  action($trigger);
              }, o.interval);        
              $thislink.click(function() {
                  $thislink.blur();
                  if ($thislink.attr('href')== '#') {
                      $thislink.blur();
                      return false;
                  }
              });
          }
      });
      if (o.event != 'click') {$(Obj).delegate('a.trigger', 'mouseleave', function() {window.clearTimeout(hTimeout); });}
      
      /* -----------------------------------------------
      // http://www.learningjquery.com/2007/10/improved-animated-scrolling-script-for-same-page-links:
      -------------------------------------------------- */
      function scrollableElement(els) {
        for (var i = 0, argLength = arguments.length; i < argLength; i++) {
          var el = arguments[i],
              $scrollElement = $(el);
          if ($scrollElement.scrollTop() > 0) {
            return el;
          } else {
            $scrollElement.scrollTop(1);
            var isScrollable = $scrollElement.scrollTop() > 0;
            $scrollElement.scrollTop(0);
            if (isScrollable) {
              return el;
            }
          }
        };
        return [];
      }; 
      /* ----------------------------------------------- */
});};
$.fn.nestedaccordion.defaults = {
  container : true, // {true} if the plugin is called on the closest named container, {false} if the pligin is called on the nestedaccordion element
  obj : 'ul', // the element which contains the nestedaccordion - 'ul', 'ol', 'div' 
  objClass : '.nestedaccordion', // the class name of the nestedaccordion - required if you call the nestedaccordion on the container
  objID : '', // the ID of the nestedaccordion (optional)
  wrapper :'li', // the common parent of 'a.trigger' and 'o.next' - 'li', 'div'
  el : 'li', // the parent of 'a.trigger' - 'li', '.h'
  head : '', // the headings that are parents of 'a.trigger' (if any)
  next : 'ul', // the collapsible element - 'ul', 'ol', 'div'
  initShow : '', // the initially expanded section (optional)
  expandSub : true, // {true} forces the sub-content under the 'current' item to be expanded on page load
  showMethod : 'slideDown', // 'slideDown', 'show', 'fadeIn', or custom
  hideMethod : 'slideUp', // 'slideUp', 'hide', 'fadeOut', or custom
  showSpeed : 200,
  hideSpeed : 400,
  scrollSpeed : 600, //speed of repositioning the newly opened section when it is pushed off screen.
  activeLink : true, //{true} if the nestedaccordion is used for site navigation
  event : 'click', //'click', 'hover'
  focus : true, // it is needed for  keyboard accessibility when we use {event:'hover'}
  interval : 400, // time-interval for delayed actions used to prevent the accidental activation of animations when we use {event:hover} (in milliseconds)
  collapsible : true, // {true} - makes the nestedaccordion fully collapsible, {false} - forces one section to be open at any time
  standardExpansible : false, //if {true}, the functonality will be standard Expand/Collapse without 'nestedaccordion' effect
  lastChild : true, //if {true}, the items without sub-elements will also trigger the 'nestedaccordion' animation
  shift: false, // false, 'clicked', 'all'. If 'clicked', the clicked item will be moved to the first position inside its level, 
                // If 'all', the clicked item and all following siblings will be moved to the top
  elToWrap: null, // null, or the element, besides the text node, to be wrapped by the trigger, e.g. 'span:first'
  uri : 'full', // 
  retFunc: null //
};
/* ---------------------------------------------
Feel free to remove the following code if you don't need these custom animations.
------------------------------------------------ */
//credit: http://jquery.malsup.com/fadetest.html
$.fn.slideFadeDown = function(speed, callback) { 
  return this.animate({opacity: 'show', height: 'show'}, speed, function() { 
    if (jQuery.browser.msie) { this.style.removeAttribute('filter'); }
    if (jQuery.isFunction(callback)) { callback(); }
  }); 
}; 
$.fn.slideFadeUp = function(speed, callback) { 
  return this.animate({opacity: 'hide', height: 'hide'}, speed, function() { 
    if (jQuery.browser.msie) { this.style.removeAttribute('filter'); }
    if (jQuery.isFunction(callback)) { callback(); }
  }); 
}; 
/* --- end of the optional code --- */
})(jQuery);
///////////////////////////
// The plugin can be called on the ID of the nestedaccordion element or on the ID of its closest named container.
// If the plugin is called on a named container, we can initialize all the nestedaccordions residing in a given section with just one call.
// EXAMPLES:
/* ---
$(function() {
// If the closest named container = #container1 or the nestedaccordion element is <ul id="subnavigation">:
/// Standard nested lists:
  $('#container1').nestedaccordion(); // we are calling the plugin on the closest named container
  $('#subnavigation').nestedaccordion({container:false}); // we are calling the plugin on the nestedaccordion element
  // this will expand the sub-list with "id=current", when the nestedaccordion is initialized:
  $('#subnavigation').nestedaccordion({container:false, initShow : "#current"});
  // this will expand/collapse the sub-list when the mouse hovers over the trigger element:
  $('#container1').nestedaccordion({event : "hover", initShow : "#current"});
 
// If the closest named container = #container2
/// Nested Lists + Headings + DIVs:
  $('#container2').nestedaccordion({el: '.h', head: 'h4, h5', next: 'div'});
  $('#container2').nestedaccordion({el: '.h', head: 'h4, h5', next: 'div', initShow : 'div.outer:eq(0)'});
  
/// Nested DIVs + Headings:
  $('#container2').nestedaccordion({obj: 'div', wrapper: 'div', el: '.h', head: 'h4, h5', next: 'div.outer'});
  $('#container2').nestedaccordion({objID: '#acc2', obj: 'div', wrapper: 'div', el: '.h', head: 'h4, h5', next: 'div.outer', initShow : '.shown', shift: 'all'});
});

/// We can globally replace the defaults, for example:
  $.fn.nestedaccordion.defaults.initShow = "#current";
--- */
/// Example options for Hover Accordion:
/* ---
$.fn.nestedaccordion.defaults.container=false;
$.fn.nestedaccordion.defaults.event="hover";
$.fn.nestedaccordion.defaults.focus=false; // Optional. If it is possible, use {focus: true}, since {focus: false} will break the keyboard accessibility
$.fn.nestedaccordion.defaults.initShow="#current";
$.fn.nestedaccordion.defaults.lastChild=false;
--- */