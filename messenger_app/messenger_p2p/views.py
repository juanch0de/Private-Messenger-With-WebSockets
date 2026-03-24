from django.shortcuts import render

def index(request):
    return render(request, 'messenger_p2p/index.html')

# Create your views here.
