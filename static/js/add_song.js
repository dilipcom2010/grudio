$(document).ready(function() {
	$("#submit").click(function() {
		//alert("working");
		$("#submit").val("Validating song...");
		$("#submit").attr("disabled", "disabled");
		$("#alert").css("display", "none");
		var actionUrl = window.location;

		var formData = {};
		formData.name = $("#name").val();
		formData.url = $("#url").val();
		formData._xsrf = getCookie("_xsrf");
		console.log(formData);

		// AJAX Code To Submit Form.
		$.ajax({
			type: "POST",
			url: actionUrl,
			data: $.param(formData),
			dataType:"text",
			cache: false,
			success: function(result) {
				result = jQuery.parseJSON(result);
				$("#alert").css("display", "block");
				if(!result.success){
					$("#alert").removeClass("alert-success");
					$("#alert").addClass("alert-danger");
					$("#alert").html(result.error);
				}else{
					$("#alert").removeClass("alert-danger");
					$("#alert").addClass("alert-success");
					$("#alert").html("<strong>Well done!</strong> "+result.success);
				}
				$("#name").val("");
				$("#url").val("");
				$("#submit").val("Add song");
				$('#submit').removeAttr("disabled");
			},
			error: function(XMLHttpRequest, textStatus, errorThrown) {
				console.log(textStatus);
				console.log(XMLHttpRequest);
				//alert("Status: " + textStatus);
				//alert("Error: " + errorThrown);
			}
		});
		return false;
	});
});


function getCookie(name) {
	var r = document.cookie.match("\\b" + name + "=([^;]*)\\b");
	return r ? r[1] : undefined;
}
