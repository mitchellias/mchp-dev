/*
 * calendar.js
 *
 * This file handles the functionality of the calendar page.
 */
$(function() {
	if($('#calStepOne').length) {
		$('#yourCalList').hide();
	}
	// show calendar step three  when clicked
    $('.stepOneNext').on('click', function () {
    	$('#calStepOne').fadeOut(250, function () {
    		$('#calStepTwo').fadeIn(500);
    		$('#calStepTwo').removeClass("hidden");
    	});
	});
	// show calendar step three when clicked
    $('.stepTwoNext').on('click', function () {
	$('#calStepTwo').fadeOut(250, function () {
		$('#calStepThree').fadeIn(500);
		$('#calStepThree').removeClass("hidden");
		});
	});
	// switch to your cal list when clicked and close intro
	$('.stepThreeNext').on('click', function () {
		$('.cal-intro').fadeOut(250, function () {
			$('#yourCalList').fadeIn(500);
		});
		toggle_flag('calendar_tutorial');
	});

	// using jquery.cookie plugin
	var csrftoken = $.cookie('csrftoken');
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

	$('#confirm-delete-button').click(function() {
		var pk = $(this).data('cal');
		deleteCalendar(pk);
		var $link_parent = $('#owned-calendar-holder-'+pk);
		$link_parent.fadeOut(500, function() {
			$link_parent.remove();
			var count = parseInt($('#owned-calendar-count').text()) - 1;
			$('#owned-calendar-count').text(count);
			if (count < 1) {
				$('#make-a-calendar').removeClass('hidden');
			}
		});
	});

	$('.pre-delete-button').click(function() {
		var $modal = $('#delete-cal-modal');
		var pk = $(this).data('cal');
		$('#confirm-delete-button').data('cal', pk);
		$modal.modal('show');
	});

	/**********************
	 * FULLCALENDAR STUFF *
	 **********************/

	var today = new Date().toJSON().slice(0,10);
	var updateEvent = function(event, dateDelta, minuteDelta) {
		eventData = {
			id: event.id,
			title: event.title,
			start: event.start.toJSON(),
			end: event.end.toJSON(),
			all_day: event.allDay,
		};
		saveEvent(eventData, false);
	};

	$('#calendar').fullCalendar({
		header: false,
    	weekMode: 'liquid',

		//trigger add event pop-up on click and stay
		dayClick: function(date, jsEvent, view) {
			// remove the other popovers
			$('.popover').remove();
			// show the clicked day popover
			date_string = date.format('ddd MMM DD, YYYY');
			$('.date-input').data('date', date);
			$('.date-input').attr('value', date_string);

			console.log($(this));
			$(this).popover('show');
		},
		
		events: {
			url: '/calendar/feed/',
			type: 'GET',
			success: function(data) {
				var event_dates = [];
				$.each(data, function(index, date) {
					event_dates.push({
							'start': moment(date.start),
							'end': moment(date.end),
							'count': date.created_count,
					});
				});
				$('.fc-day').each(function() {
					// Get current day
					day = moment($(this).data('date'));
					// if this day has an event
					if (event_dates.length && event_dates[0].start.diff(day, 'days') < 1) {
						var count = event_dates[0].count;
						var $cal_day = $(this);
						// create a new canvas element the size of the cal day
						var $canvas = $('<canvas id="canvas-'+
							day.format('YYYY-M-DD') +
							'" class="'+ 
							"canvas-day" + 
							'" height="'+ 
							$cal_day.height()+
							'" width="'+
							$cal_day.width()+
							'" data-count="'+
							count+
							'"></canvas>');
						$cal_day.html($canvas);
						drawCircle($canvas.get(0));

						// remove the event count from the array
						event_dates.shift();
					}
				});
			},
			error: function() {
				addMessage('Error getting events', 'danger');
			},
		},
		eventRender: function(event, element) {
			// don't show the fullcalendar events
			return false;
		},
		eventClick: function(calEvent, jsEvent, view) {
			eventData = {
				id: calEvent.id,
				title: calEvent.title,
				start: calEvent.start.toJSON(),
				end: calEvent.end.toJSON(),
				all_day: calEvent.allDay,
			};
			console.log(calEvent);
			$event = $(jsEvent.target).parents('.fc-event-container');
			console.log($event);
			console.log($event[0]);
			console.log($($event[0]));
			$event.popover('show');
			// deleteEvent(eventData);
			// $('#calendar').fullCalendar('removeEvents', calEvent.id);
			return false;
		},
		eventDrop: updateEvent,
		eventResize: updateEvent,

		editable: true,
		timezone: 'local',
	});

	/*****************
	 * popover stuff *
	 *****************/
	// initalize the popovers for individual cal days
	$('.fc-day').popover({
		trigger: 'manual',
		placement: 'auto left',
		html: true,
		viewport: '#calendar',
		title: function() {
			return $('#popover-title').html();
		},
		content: function() {
			return $('#popover-content').html();
		},
		container: 'body',
	});
	$('#calendar').on('mouseleave', '.canvas-day', function() {
		$(this).popover({
			trigger: 'hover',
			placement: 'auto',
			html: true,
			viewport: '#calendar',
			title: function() {
				return $('#popover-title').html();
			},
			content: function() {
				return $('#popover-content').html();
			},
			container: 'body',
		});
		$('.popover').remove();
		$(this).popover('show');
	});

	$('#calendar').on('click', '.canvas-day', function(event) {
		var $day = $(event.target).parent();
		$day.trigger('click');
	});

	$('canvas').popover({
		trigger: 'hover',
		placement: 'auto top',
		html: true,
		viewport: '#calendar',
		title: function() {
			return 'wat'; 
		},
		content: function() {
			return 'um';
		},
		container: 'body',
	});

	var observer = new MutationObserver(function(mutations) {
		alert('what');
		mutations.forEach(function(mutation) {
		});
	});
	// configuration of the observer:
	var config = { attributes: true, childList: true, characterData: true };
	// pass in the target node, as well as the observer options
	observer.observe($('.fc-day-grid').get(0), config);

	// close the popovers when you click outside
	// this is add to the body so it can be registered
	// with dynamically added popovers
	$('body').on('click', function (event) {
		var $target = $(event.target);
		// this makes baby pandas around the world cry salty tears
		if(!($target.hasClass('btn') ||
				 $target.hasClass('day') ||
				 $target.hasClass('date') ||
				 $target.hasClass('fc-day') ||
				 $target.hasClass('popover-title') ||
				 $target.hasClass('popover-content') ||
				 $target.hasClass('datepicker-switch') ||
				 $target.hasClass('datepicker-days') ||
				 $target.hasClass('table-condensed') ||
				 $target.hasClass('prev') ||
				 $target.hasClass('next') ||
				 $target.hasClass('dow') ||
				 $target.is('span') ||
				 $target.is('a') ||
				 $target.hasClass('form-control')
				)) {
			$('.popover').popover('hide');
		}
		// when you click on any of the list items in the drop down
    	$("#calSelect > li a").click(function(){
			// replace the cal icon with the title of the calendar
	        $(".cal-name").text($(this).text() + ' ');
	        $(".cal-name").data('calendar', $(this).data('calendar'));
    	});

    	//display selected due date time in create event popover button addon
    	$("#duedateSelect > li a").click(function(){
	        //display the selected calendar in the button
	        $(".due-date").text($(this).text() + ' ');
	        $(".due-date").data('due', $(this).data('due'));
    	});
    	// initialize date picker
		$('input.date').datepicker({
			format: "D M d, yyyy", //"yyyy-m-d"
		    startDate: "today",
			autoclose: true,
			todayHighlight: true
	    }).on('changeDate', function(event) {
			var pick = moment(event.date);
			$('.date-input').data('date', pick);
		});
	});


	// submitting the form in the popover
	$('body').on('submit', '#add-event-form', function(event) {
		var $form = $(event.target);
		var url = '/calendar/events/add/';
		var messages = [];
		var data = $form.serialize();

		// which calendar this event is for 
		var cal = $('.cal-name').data('calendar');
		cal = JSON.stringify(cal);
		data += "&calendar=" + encodeURIComponent(cal);

		// approx. time it is due
		var due = $('.due-date').data('due');
		due_json = JSON.stringify(due);
		data += "&due=" + encodeURIComponent(due_json);

		var date = $('.date-input').data('date');
		date_json = JSON.stringify(date);
		data += "&date=" + encodeURIComponent(date_json);

		$.ajax({
			url: url,
			type: 'POST',
			data: data,
			success: function(data) {
				messages = data.messages;
				// add the event to the calendar
				var event = JSON.parse(data.event);
				$cal = $('#calendar');
				$cal.fullCalendar('renderEvent', event[0].fields);

				var iso = moment(date).format('YYYY-M-DD');
				var $canvas = $('#canvas-'+iso);
				var count = parseInt($canvas.data('count')) + 1;
				$canvas.data('count', count);
				drawCircle($canvas);
			},
			fail: function(data) {
				addMessage('Failed to save event', 'danger');
			},
			complete: function(data) {
				$.each(messages, function(index, message){
					addMessage(message.message, message.extra_tags);
				});
			},

		});
		$('.popover').popover('hide');
		return false;
	});

	//Create cal event with button
	$('#createOptions').popover({
		trigger: 'focus',
		placement: 'bottom',
		html: true,
		// viewport: '#calendar',
		title: function() {
			return $('#newEventTitle').html();
		},
		content: function() {
			return $('#newEventContent').html();
		},
		container: 'body',
	});

	/*********************************
	 * CUSTOM HEADER BUTTONS FOR CAL *
	 *********************************/
	//	custom date above calendar 
	$('.cal-date').html(function () {
		var view = $('#calendar').fullCalendar('getView');
		return view.title;
	});

	// today button
	$('.cal-today-button').click(function() {
    	$('#calendar').fullCalendar('today');
	});

	// prev button
	$('.cal-prev-button').click(function() {
    	$('#calendar').fullCalendar('prev');
	});
	// next button
	$('.cal-next-button').click(function() {
    	$('#calendar').fullCalendar('next');
	});
	// month view button
	$('.cal-month-button').click(function() {
    	$('#calendar').fullCalendar( 'changeView', 'month' );
	});
	// agenda week view button
	$('.cal-agendaWeek-button').click(function() {
    	$('#calendar').fullCalendar( 'changeView', 'agendaWeek' );
	});
	// agenda day view button
	$('.cal-agendaDay-button').click(function() {
    	$('#calendar').fullCalendar( 'changeView', 'agendaDay' );
	});

	// change the title when the view changes
	$('.cal-button').click(function() {
    	$('.cal-date').text(function () {
			var view = $('#calendar').fullCalendar('getView');
			return view.title;
		});
	});

	//toggle calendar list section
    $('.viewCals').on('click', function () {
        $('.flip-holder').toggleClass("flip");
    });

});

var saveEvent = function (eventData, create) {
	var url = '';
	if (create) {
		url = '/calendar/events/add/';
	} else {
		url = '/calendar/events/update/';
	}
	$.ajax({
		url: url,
		type: 'POST',
		data: eventData,
		success: function(data) {
			$.each(data.messages, function(index, message){
				addMessage(message.message, message.extra_tags);
			});
		},
		fail: function(data) {
			addMessage('Failed to save event', 'danger');
		},
		complete: function(data) {
		},
	});
};

var deleteEvent = function(eventData) {
	$.ajax({
		url: '/calendar/events/delete/',
		type: 'POST',
		data: eventData,
		success: function(data) {
			$.each(data.messages, function(index, message){
				addMessage(message.message, message.extra_tags);
			});
		},
		fail: function(data) {
			addMessage('Failed to delete event', 'danger');
		},
		complete: function(data) {
		},
	});
};


var deleteCalendar = function(cal_pk) {
	var messages = [];
	$.ajax({
		url: '/calendar/delete/',
		type: 'POST',
		data: {
			'id': cal_pk,
		},
		dataType: 'json',
		success: function(data) {
		},
		fail: function(data) {
		},
		complete: function(data) {
			messages = data.responseJSON.messages;
			$.each(messages, function(index, message){
				addMessage(message.message, message.extra_tags);
			});
		},
	});
};
var drawCircle = function(canvas) {
	var count = $(canvas).data('count');

	if (canvas.getContext){
		var ctx = canvas.getContext('2d');
		ctx.clearRect(0, 0, canvas.width, canvas.height);

		ctx.beginPath();
		var x              = $(canvas).width() / 2;               // x coordinate
		var y              = $(canvas).height() / 2;               // y coordinate
		var radius         = $(canvas).width() / 4;                    // Arc radius
		var startAngle     = 0;                     // Starting point on circle
		var endAngle       = Math.PI * 2; // End point on circle
		var anticlockwise  = true; // clockwise or anticlockwise

		ctx.arc(x, y, radius, startAngle, endAngle, anticlockwise);

		ctx.fillStyle="#4C9ED9";
		ctx.fill();
		ctx.fillStyle="#FFFFFF";

		var font_x = parseInt(y*(2/3)).toString();
		ctx.font = font_x  + "pt Arial";
		var text_start = ctx.measureText(count);
		ctx.fillText(count, x-text_start.width/2, y + (y*(1/4)));
  }
};
