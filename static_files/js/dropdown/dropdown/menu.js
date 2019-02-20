function mainmenu(){
$(" #nav ul ").css({display: "none"}); // Opera Fix
$(" #nav li").click(function(){
		$(this).find('ul:first').css({visibility: "visible",display: "none"}).show(100);
		},
		
function(){
		$(this).find('ul:first').css({visibility: "visible"});
		});		
}
$("div").click(function(){
 $(this).css ({visibility: "visible",display: "none"}).show(100);
})
$(" #primero div ").css({display:"block"});

$(" #segundo div ").css({display:"none"});

$(" #tercero div ").css({display:"none"});
 
 
 $(document).ready(function(){					
	mainmenu();
});