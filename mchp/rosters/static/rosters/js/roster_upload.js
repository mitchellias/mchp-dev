/*
 * upload_roster.js
 *
 * This file is for the roster upload page
 */
"use strict";  // ECMAScript 5

$(document).ready(function() {
    $.fn.editable.defaults.mode = 'inline';

    // Bootstrap Editable form fields

    // make the newly added fields editable
    $(".editField").editable({
        type: "email",
        highlight: "#000",
        showbuttons: false,
        anim: "med",
        onblur: 'submit'
    });

    $('.examSelect').editable({
        type: "select",
        showbuttons: false,
        anim: "med",
        onblur: 'submit',
        value: 1,
        source: [
            {value: 1, text: 'Exam 1'},
            {value: 2, text: 'Exam 2'},
            {value: 3, text: 'Exam 3'}
        ]
    });

    $('.rosterCode').editable({
        inputclass: "input-sm",
        showbuttons: false,
        anim: "med",
        onblur: 'submit',
        rows: 10
    });

    // When a user clicks to add a new instructor email, show them a new field

    $("#addInstructorEmail").click(function () {
        var nextListItem = $("#InstructorEmails").find("li.additionalInstr:hidden:first");
        nextListItem.removeClass("hidden");
    });
});


