from django.shortcuts import render, redirect
from .forms import DocumentUploadForm, SearchForm, MODEL_CHOICES
from .forms import TagForm, PhilosophyUploadForm, PersonaUploadForm, VoiceUploadForm, ToneUploadForm, OutputFormatUploadForm
from .models import Document, Philosophy, Persona, Voice, Tone, ChatMessage, ChatSession, UserProfile, OutputFormat, Tag, PineconeDocument
from .utils import extract_text_from_file, store_document_in_pinecone, search_similar_chunks
from pinecone import Pinecone, ServerlessSpec, PineconeApiException
from django.shortcuts import redirect, get_object_or_404
from django.views.decorators.csrf import csrf_protect
from decouple import config
from django.urls import reverse
from urllib.parse import urlencode
from django.http import HttpResponseForbidden, HttpResponseBadRequest, HttpResponse, FileResponse, Http404
import os
from django.views.decorators.http import require_POST
from django.contrib import messages
from django.contrib.auth.decorators import login_required

PINECONE_API_KEY = config('PINECONE_API_KEY')
pc = Pinecone(api_key=PINECONE_API_KEY)


index_name = "yourpeak-gpt"

if index_name not in pc.list_indexes().names():
    pc.create_index(
        name=index_name,
        dimension=3072,
        metric='cosine',
        spec=ServerlessSpec(cloud='aws', region='us-east-1')
    )
index = pc.Index(index_name)

def admin_dashboard_view(request):
    if not request.user.is_authenticated:
        return redirect('login')

    try:
        profile = UserProfile.objects.get(user=request.user)
        if profile.role != 'admin':
            return redirect('home_screen')
    except UserProfile.DoesNotExist:
        return redirect('home_screen')
    # Initialize forms
    pinecone_docs = PineconeDocument.objects.select_related('document').all()
    tag_form = TagForm()
    philosophy_form = PhilosophyUploadForm()
    persona_form = PersonaUploadForm()
    voice_form = VoiceUploadForm()
    tone_form = ToneUploadForm()
    format_form = OutputFormatUploadForm()

    if request.method == 'POST':
        if 'upload_tag' in request.POST:
            tag_form = TagForm(request.POST)
            if tag_form.is_valid():
                tag_form.save()
                messages.success(request, "Tag added.")
                return redirect('admin_dashboard')

        elif 'upload_philosophy' in request.POST:
            philosophy_form = PhilosophyUploadForm(request.POST, request.FILES)
            if philosophy_form.is_valid():
                philosophy_form.save()
                messages.success(request, "Philosophy uploaded.")
                return redirect('admin_dashboard')

        elif 'upload_persona' in request.POST:
            persona_form = PersonaUploadForm(request.POST, request.FILES)
            if persona_form.is_valid():
                persona_form.save()
                messages.success(request, "Persona uploaded.")
                return redirect('admin_dashboard')

        elif 'upload_voice' in request.POST:
            voice_form = VoiceUploadForm(request.POST, request.FILES)
            if voice_form.is_valid():
                voice_form.save()
                messages.success(request, "Voice uploaded.")
                return redirect('admin_dashboard')

        elif 'upload_tone' in request.POST:
            tone_form = ToneUploadForm(request.POST, request.FILES)
            if tone_form.is_valid():
                tone_form.save()
                messages.success(request, "Tone uploaded.")
                return redirect('admin_dashboard')

        elif 'upload_format' in request.POST:
            format_form = OutputFormatUploadForm(request.POST, request.FILES)
            if format_form.is_valid():
                format_form.save()
                messages.success(request, "Output format uploaded.")
                return redirect('admin_dashboard')

    users = UserProfile.objects.select_related('user').all()

    philosophy_files = Philosophy.objects.all()
    persona_files = Persona.objects.all()
    voice_files = Voice.objects.all()
    tone_files = Tone.objects.all()
    format_files = OutputFormat.objects.all()
    tags = Tag.objects.all()
    pinecone_docs = PineconeDocument.objects.all().order_by('-uploaded_at')
    context = {
        'users': users,
        'tag_form': tag_form,
        'philosophy_form': philosophy_form,
        'persona_form': persona_form,
        'voice_form': voice_form,
        'tone_form': tone_form,
        'format_form': format_form,
        'philosophy_files': philosophy_files,
        'persona_files': persona_files,
        'voice_files': voice_files,
        'tone_files': tone_files,
        'format_files': format_files,
        'tags': tags,
        'pinecone_documents': pinecone_docs,
    }
    return render(request, 'lesson_plans/admin-dashboard.html', context)


@require_POST
@login_required
def update_user_role(request):
    user_profile = UserProfile.objects.get(user=request.user)
    if user_profile.role != 'admin':
        return HttpResponseForbidden("You are not authorized to perform this action.")

    user_id = request.POST.get('user_id')
    new_role = request.POST.get('new_role')

    try:
        target_profile = UserProfile.objects.get(user__id=user_id)
        target_profile.role = new_role
        target_profile.save()
        messages.success(request, f"{target_profile.user.username}'s role updated to {new_role}.")
    except UserProfile.DoesNotExist:
        messages.error(request, "User not found.")

    return redirect('admin_dashboard')


MODEL_MAP = {
    'philosophy': Philosophy,
    'persona': Persona,
    'voice': Voice,
    'tone': Tone,
    'outputformat': OutputFormat,
    'tag': Tag,
}

@login_required
def delete_file(request, model, file_id):
    if request.method == 'POST':
        model_class = MODEL_MAP.get(model.lower())
        if not model_class:
            return HttpResponseBadRequest("Invalid model type.")

        try:
            file_obj = model_class.objects.get(id=file_id)

            # If object has an `uploaded_by` field, restrict deletion
            if hasattr(file_obj, 'uploaded_by') and file_obj.uploaded_by != request.user:
                return HttpResponseForbidden("You do not have permission to delete this item.")

            # Always delete the database object
            file_obj.delete()
        except model_class.DoesNotExist:
            pass

    return redirect('admin_dashboard')

@login_required
def view_file(request, model, file_id):
    Model = MODEL_MAP.get(model.lower())
    if not Model:
        return HttpResponse("Invalid model type.", status=400)

    try:
        file_obj = Model.objects.get(id=file_id)
        file_path = file_obj.file.path
        ext = os.path.splitext(file_path)[1].lower()

        if ext in ['.txt', '.md', '.csv', '.json']:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            return HttpResponse(f"<pre>{content}</pre>")
        else:
            return HttpResponse("This file type is not viewable as plain text.", status=415)

    except Model.DoesNotExist:
        return HttpResponse("File not found.", status=404)

@login_required
def download_file(request, category, file_id):
    Model = MODEL_MAP.get(category)
    if not Model:
        raise Http404("Invalid category")

    try:
        obj = Model.objects.get(id=file_id)
        file_path = obj.file.path
        file_name = os.path.basename(file_path)
        return FileResponse(open(file_path, 'rb'), as_attachment=True, filename=file_name)
    except (Model.DoesNotExist, FileNotFoundError):
        raise Http404("File not found")

@login_required
def delete_pinecone_document(request, doc_id):
    if request.method == 'POST':
        pinecone_doc = get_object_or_404(PineconeDocument, id=doc_id)

        try:
            # Delete vectors from Pinecone
            vector_ids = pinecone_doc.vector_ids
            index.delete(ids=vector_ids)

            # Delete local records
            pinecone_doc.document.delete()  # Also deletes the related PineconeDocument due to CASCADE
            messages.success(request, "Document and its vectors were deleted successfully.")
        except PineconeApiException as e:
            messages.error(request, f"Pinecone API error: {str(e)}")
        except Exception as e:
            messages.error(request, f"Error: {str(e)}")

    return redirect('admin_dashboard')

def upload_document(request):
    if not request.user.is_authenticated:
        return redirect('login')

    try:
        profile = UserProfile.objects.get(user=request.user)
        if profile.role != 'admin':
            return redirect('home_screen')
    except UserProfile.DoesNotExist:
        return redirect('home_screen')
    if request.method == 'POST':
        form = DocumentUploadForm(request.POST, request.FILES)
        if form.is_valid():
            document = form.save(commit=False)
            uploaded_file = request.FILES['file']

            try:

                content = extract_text_from_file(uploaded_file)
                document.content = content
                document.save()
                form.save_m2m()

                try:
                    store_document_in_pinecone(document)
                    base_url = reverse('upload_document')
                    query_string = urlencode({'success': '1'})
                    return redirect(f"{base_url}?{query_string}")
                    # return redirect('document_list')
                except Exception as e:
                    return render(request, 'lesson_plans/upload_document.html', {
                        'form': form,
                        'error': f"Failed to store in Pinecone: {str(e)}"
                    })
            except Exception as e:
                return render(request, 'lesson_plans/upload_document.html', {
                    'form': form,
                    'error': f"Failed to process file: {str(e)}"
                })
    else:
        form = DocumentUploadForm()

    return render(request, 'lesson_plans/upload_document.html', {'form': form})

def semantic_search(query):
    from difflib import SequenceMatcher
    docs = Document.objects.all()
    results = []

    for doc in docs:
        score = SequenceMatcher(None, query.lower(), doc.text.lower()).ratio()
        if score > 0.3:
            results.append({
                'text': doc.text,
                'score': score
            })

    return sorted(results, key=lambda x: x['score'], reverse=True)


@csrf_protect
def delete_chat(request, chat_id):
    if not request.user.is_authenticated:
        return redirect('login')

    if request.method == 'POST':
        # Only fetch chats owned by the logged-in user
        chat = get_object_or_404(ChatSession, id=chat_id, user=request.user)
        chat.delete()

    # Redirect to remaining chats owned by the same user
    remaining_chat = ChatSession.objects.filter(user=request.user).first()
    if remaining_chat:
        return redirect(f"/search/?chat_id={remaining_chat.id}")
    return redirect("/search/")


def search_view(request):
    if not request.user.is_authenticated:
        return redirect('home_screen')

    try:
        profile = UserProfile.objects.get(user=request.user)
        if profile.role not in ['admin', 'client']:
            return redirect('home_screen')
    except UserProfile.DoesNotExist:
        return redirect('home_screen')
    form = SearchForm(request.GET or None)
    results, answer = [], None
    selected_ids = {
        "philosophy_ids": [],
        "persona_ids": [],
        "voice_id": None,
        "tone_ids": [],
        "outputformat_id": None,
        "model": "gpt-4o-mini-2024-07-18",
    }

    chat_id = request.GET.get("chat_id")
    new_chat_requested = request.GET.get("new_chat")

    # Chat session handling
    if chat_id:
        try:
            # chat_session = ChatSession.objects.get(id=chat_id)
            chat_session = get_object_or_404(ChatSession, id=chat_id, user=request.user)


            is_empty_chat = (
                chat_session.messages.count() == 0 and
                not chat_session.title
            )

            # If user requested a new chat but is already in an empty one, just stay here
            if new_chat_requested and is_empty_chat:
                return redirect(f"/search/?chat_id={chat_session.id}")

        except ChatSession.DoesNotExist:
            # chat_session = ChatSession.objects.create()
            chat_session = ChatSession.objects.create(user=request.user)
            return redirect(f"/search/?chat_id={chat_session.id}")
    elif new_chat_requested:
        empty_chats = ChatSession.objects.filter(user=request.user, messages__isnull=True, title="")
        if empty_chats.exists():
            chat_session = empty_chats.first()
        else:
            chat_session = ChatSession.objects.create(user=request.user)
        return redirect(f"/search/?chat_id={chat_session.id}")
    else:
        empty_chats = ChatSession.objects.filter(user=request.user, messages__isnull=True, title="")
        if empty_chats.exists():
            chat_session = empty_chats.first()
        else:
            chat_session = ChatSession.objects.create(user=request.user)
        return redirect(f"/search/?chat_id={chat_session.id}")


    if request.method == 'GET' and form.is_valid() and 'query' in request.GET:
        query = form.cleaned_data['query']
        selected_ids["philosophy_ids"] = list(map(int, request.GET.getlist("philosophy")))
        selected_ids["persona_ids"] = list(map(int, request.GET.getlist("personas")))
        selected_ids["voice_id"] = form.cleaned_data.get("voice").id if form.cleaned_data.get("voice") else None
        selected_ids["tone_ids"] = [tone.id for tone in form.cleaned_data.get("tones")] if form.cleaned_data.get("tones") else []
        selected_ids["outputformat_id"] = form.cleaned_data.get("outputformat").id if form.cleaned_data.get("outputformat") else None
        selected_ids["model"] = form.cleaned_data.get("model") or selected_ids["model"]

        user_msg = ChatMessage.objects.create(session=chat_session, role="user", content=query)

        if not chat_session.title and chat_session.messages.count() == 1:
            trimmed_title = " ".join(query.split()[:6])
            if len(query.split()) > 6:
                trimmed_title += "..."
            chat_session.title = trimmed_title
            chat_session.save()

        try:
            result_data = search_similar_chunks(query, top_k=5, use_gpt=True, **selected_ids)

            if isinstance(result_data, dict):
                answer = result_data.get("answer")
                results = result_data.get("chunks", [])

                assistant_msg = ChatMessage.objects.create(session=chat_session, role="assistant", content=answer)
                print("[DEBUG] Created assistant message:", assistant_msg.id)

        except Exception as e:
            return render(request, "lesson_plans/search.html", {
                "form": form,
                "query": query,
                "results": [],
                "error": f"Error: {str(e)}",
                "philosophies": Philosophy.objects.all(),
                "personas": Persona.objects.all(),
                "voices": Voice.objects.all(),
                "tones": Tone.objects.all(),
                "outputformats": OutputFormat.objects.all(),
                "chat_id": chat_id,
                "messages": ChatMessage.objects.filter(session=chat_session),
                # "sessions": ChatSession.objects.all(),
                "sessions": ChatSession.objects.filter(user=request.user),
                **selected_ids
            })

    context = {
        "form": form,
        "query": request.GET.get("query", ""),
        "results": results,
        "answer": answer,
        "philosophies": Philosophy.objects.all(),
        "personas": Persona.objects.all(),
        "voices": Voice.objects.all(),
        "tones": Tone.objects.all(),
        "outputformats": OutputFormat.objects.all(),
        "chat_id": chat_id,
        "messages": ChatMessage.objects.filter(session=chat_session),
        # "sessions": ChatSession.objects.all(),
        "sessions": ChatSession.objects.filter(user=request.user),
        "selected_philosophy_ids": selected_ids.get("philosophy_ids", []),
        "selected_persona_ids": selected_ids.get("persona_ids", []),
        **selected_ids
    }

    return render(request, "lesson_plans/search.html", context)

# touched on 2025-06-13T18:49:51.142954Z
# touched on 2025-06-13T18:50:08.929891Z