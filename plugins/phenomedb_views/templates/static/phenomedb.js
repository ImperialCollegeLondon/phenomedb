
	
function highlightTableRow(itemInRow) {
	$(itemInRow).closest("tr").addClass("selected-row");
	$(itemInRow).closest("tr").siblings().removeClass("selected-row");
}



function makeGlyphButton(glyphName) {	
	var icon = $("<span/>"); 
	icon.addClass("glyphicon " + glyphName);
	icon.attr("aria-hidden", "true");			
	var btn = $("<a>").attr("href", "#");
	btn.append(icon);
	return btn;
}

function serializeForm(form) {
	var serialized = {};
	$
	.each(
		form.serializeArray(),
		function() {
			serialized[this.name] = serialized[this.name] ? serialized[this.name].split(','): [];
			serialized[this.name] = serialized[this.name].concat(this.value).join(',');
		});
	console.log("serializeForm is " + JSON.stringify(serialized));
	return serialized;
};

function getFileSizeNameAndType(inputId)	{

	var fi = $('#' + inputId)[0]; 	
	var totalFileSize = 0;
    var fsize = fi.files.item(0).size;
    totalFileSize = totalFileSize + fsize;
    fi.innerHTML = '<b>' + fi.files.item(0).name + '</b>, size <b>' + Math.round((fsize / 1024)) +
    	'</b> KB, <b>' + fi.files.item(0).type + "</b>.";

	var s = Math.round(totalFileSize / 1024);
	console.log( "Total File(s) Size is <b>" + s + "</b> KB");
};

function ajaxPostForm( objForm) {
	var formTarget = objForm.attr('action');
	formJSON = JSON.stringify( serializeWithLists( objForm ) );

	var jqxhr = $.ajax({			
	  processData: false,
	  method: 'POST',
	  url: formTarget,
	  contentType: 'application/json',
	  dataType: "json",
	  data: formJSON
	});	 
	return jqxhr;
};

function ajaxUpdateOrDelete( obj, url, httpMethod, csrf_token, beforeMsg ) {
	console.log("update or delete " + JSON.stringify(obj));
	var jqxhr = $.ajax({
		  beforeSend: function( xhr ) {
				if ( beforeMsg.length > 0 )  
					return confirm(beforeMsg); 
				else return true;
		  },
		  headers: {"X-CSRFToken": csrf_token },
		  processData: false,
		  method: httpMethod,
		  url: url,
		  contentType: "application/json",
		  dataType: "json",
		  data: JSON.stringify(obj)
		});
	return jqxhr;
}

$(function() {
	$.datepicker.setDefaults({
	     dateFormat: 'yy-mm-dd'
	});
	
	$("input[type=checkbox]").on("click", function(e) {
		if ( this.dataset.target ) {
			var checked = $(this).is(':checked');
	        if ( checked ) {
	        	console.log("showing " + this.dataset.target);
	            $('.' + this.dataset.target).show();
	        } else {
	        	$('.' + this.dataset.target).hide();
	        }
		}
    });
	
	$("#check-all").click(function(){
	    $('input:checkbox').not(this).prop('checked', this.checked);
	});
	
 });