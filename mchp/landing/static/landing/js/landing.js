$(function() {

    $('input[name=email]').on('focus', function() {
        $('.fa-envelope-o').removeClass('duration-infinite');
    });


    // BS Validator 
    $('#emailForm').bootstrapValidator({
        fields: {
            email: {
                trigger: 'keyup',
                validators: {
                    notEmpty: {
                        message: 'This field is required'
                    },
                    emailAddress: {
                        message: 'Please enter a valid email address'
                    },
                    regexp: {
                        regexp: /(\.edu)$/,
                        message: 'Only .EDU emails allowed'
                    }
                }
            }
        }
    });
});
