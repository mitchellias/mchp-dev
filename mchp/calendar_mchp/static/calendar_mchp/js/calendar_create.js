/*
 * calendar_create.js
 *
 * This file handles the functionality of the calendar create page.
 */
$(function() {

	// if the select changes, show sell or not sell radios
	$('.course-select').change(function() {
		$('.course-meetings').fadeIn(500).removeClass('hidden');
		$('.cal-description').fadeOut(500);
	});

	// when the clockend input changes, show cal end date field
	$('.clockend').change(function(){
		$('.cal-submit').fadeIn(500).removeClass('hidden');
	});

	// initializing clockpicker
	$('.clockpicker').clockpicker( {
		twelvehour: 'true',
		placement: 'top',
    	align: 'left',
	});

   	// when the meeting days button option changes
   	$(".day-button").click(function(event) {
		$(event.target).siblings('.day-times').fadeIn(250).toggleClass('hidden');
   	});

	// initialize date picker
	$('.date-select').datepicker({
		startView: 1,
		multidate: false,
		autoclose: true,
		todayHighlight: false
	});

	// reset form on page reload or other unload actions
	$( window ).unload(function() {
		$('#calendar-create')[0].reset();
	});	

	/***********************
	 * Submitting the form *
	 ***********************/
	$('#calendar-create').submit(function(event){
		// all the days the user selected
		var $days = $('.day-button.active');
		var times = {};
		var error = false;
		$days.each(function(index, day){
			// get the times from the user
			day_name = $(day).data('day');
			var $start = $("#" + day_name + "-clock-start");
			var $end = $("#" + day_name + "-clock-end");
			if($start.val() ==='' || $end.val()=== '') {
				addMessage('A day must have both a start and end date', 'info');
				error = true;
			}
			// parse them
			var start_moment = moment.utc($start.val(), "hh:mmA");
			var end_moment = moment.utc($end.val(), "hh:mmA");

			// validate them
			if(start_moment > end_moment) {
				error = true;
				addMessage('Start times must come before end times', 'info');
			}
			// add them to the json object
			times[day_name] = {
				'start': start_moment,
				'end': end_moment,
			};
		});
		// add object to the form
		var data = $(this).serialize();
		times = JSON.stringify(times);
		data += "&times=" + encodeURIComponent(times);

		// give this calendar a color
		// calendarColors gets added in the template for this page
		prevColors = $.map(calendarColors, function(hexColor, index) {
			// map the hex string to an rgb color
			return Please.HEX_to_RGB(hexColor);
		});

		var color = pickColor(prevColors, 50);
		var colorString = Please.RGB_to_HEX(color);
		data += "&color=" + encodeURIComponent(colorString);

		// submit the form if it was valid
		if (!error) {
			$.ajax({
				method: 'post',
				url: '/calendar/create/',
				data: data,
				success: function(data) {
					var cal = data.calendar;
					var url = "/calendar/events/add/" + "?calendar=" + cal;
					window.location.href = url;
				},
				complete: function(data) {
					if (data.hasOwnProperty('responseJSON') && data.responseJSON.hasOwnProperty('messages')) {
						$.each(data.responseJSON.messages, function(index, message) {
							addMessage(message.message, message.extra_tags);
						});
					}
				}
			});
		}
		return false;
	});
});

var calculateColorDistance = function(color1, color2) {
	var red = Math.pow((color1.r - color2.r), 2);
	var green = Math.pow((color1.g - color2.g), 2);
	var blue = Math.pow((color1.b - color2.b), 2);

	var all = red + green + blue;
	return Math.sqrt(all);
};
var pickColor = function(otherColors, threshold) {
	var candidateColor = Please.make_color({format: 'rgb'});
	if (otherColors.length === 0) {
		return candidateColor;
	}
	// function to test array colors to new generated color
	var testDifference = function(color, index) {
		var distance = calculateColorDistance(candidateColor, color);
		return distance > threshold;
	};
	var tries = 0;
	while (true) {
		tries++;
		if (tries > 100000) {
			break;
		}
		// try a new color
		candidateColor = Please.make_color({format: 'rgb'});
		// compare it to every other color in the array
		var diffs = $.map(otherColors, testDifference);
		if (diffs.indexOf(false) === -1) {
			break;
		}
	}
	return candidateColor;
};
