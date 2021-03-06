$(function(){
	// initially hide email address
	$(".show-email").hide();

	// to resend verification email
	$("#resend_form").submit(function() {

		$("#sendBtn").toggleClass("btn-success");
		$('.fa').toggleClass('fa-spin');
		setTimeout(function(){
     			// toggle back after 1 second
    				$('#sendBtn').toggleClass('btn-success');
    				$('.fa').toggleClass('fa-spin');
    				$(".show-email").show();
   					},1000);


		var url = "/profile/resend-email/"; // page just for handing resend requests

		$.ajax({
			type: "POST",
			url: url,
			data: $("#resend_form").serialize(), 
			dataType: "json",
			success: function(data) {
				$('#sendBtn').addClass('btn-primary');
				$(".show-email").hide();
				
			},
			error: function(data) {
				$('.resend_confirm').html('<p>Resend request failed.</p>');
			}
		});

		return false; 

	});
	var email = $('#saved_email').val();
	checkForConfirmation(email);
});
var checkForConfirmation = function(email) {

	var confirmUrl = "/profile/confirmed/"; // page just for seeing if the user confirmed email yet

	$.ajax({
		type: "GET",
		url: confirmUrl,
		data: {
			'email': email,
		},
		success: function(data) {
			if (data.confirmed) {
				// redirect to root, which takes you to home page, which takes you to confirm school
				// probably
				window.location.replace('/');
			} else {
				setTimeout(function() {
					checkForConfirmation(email);
				}, 1500);
			}
		},
		error: function(data) {
			// stop trying
		}
	});

};
