$(function() {

	// show saved cards on click
	$('.show-cards').on('click', function () {
		$(this).fadeOut(250, function () {
			$('.saved-cards').fadeIn(500).removeClass('hidden');
		});
	});

	$('.hide-cards').on('click', function () {
		$('.saved-cards').fadeOut(250, function () {
			$('.show-cards').fadeIn(500);
		});
	});

	// $('.show-cards').on('mouseover', function () {
	// 	$('.saved-cards').toggleClass('hidden')
	// });


	var csrftoken = $('input[name=csrfmiddlewaretoken]').val();
	function csrfSafeMethod(method) {
		// these HTTP methods do not require CSRF protection
		return (/^(GET|HEAD|OPTIONS|TRACE)$/.test(method));
	}
	// csrf token stuff
	$.ajaxSetup({
		beforeSend: function(xhr, settings) {
			if (!csrfSafeMethod(settings.type) && !this.crossDomain) {
				xhr.setRequestHeader("X-CSRFToken", csrftoken);
			}
		}
	});

	var $button = $('.delete-card-button');
	var $radios =  $('input[name=card]');
	$radios.click(function(event) {
		var $error_display = $('.card-errors');
		$error_display.text('');
		var pk = $(this).val();
		data = {
			'card': pk,
		};
		$.ajax({
			url: change_url,
			type: 'POST',
			data: data,
			success: function(data) {
				var $checkMark = $('.default-card');
				$checkMark.remove();
				console.log($checkMark);
				var $span = $('#card-span-'+pk);
				$span.prepend($checkMark);
			},
			error: function(data) {
				var errors = data.responseJSON.response;
				$error_display.text(errors);
			},
		});
	});

	$button.click(function(event) {
		var messages = [];
		var pk = $(this).data('card');

		data = {
			'card': pk,
			'delete': true,
		};

		$.ajax({
			url: change_url,
			type: 'POST',
			data: data,
			success: function(data) {
				messages = data.messages;
				$('#card-'+pk).fadeOut(500, function() {
					$('#card-'+pk).remove();
				});
			},
			error: function(data) {
				messages = data.responseJSON.messages;
			},
			complete: function(data) {
				$.each(messages, function(index, message){
					addMessage(message.message, message.extra_tags);
				});
			},
		});
	});
	// add tooltips and make sure no card is selected by default
	// tool tips don't work on calendar page
	// $(".btooltip").tooltip(); 
	$('.default-card-container input').prop('checked', false);
});
