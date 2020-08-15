from django.core.paginator import Paginator, PageNotAnInteger, EmptyPage
from django.http import HttpResponseRedirect
from django.urls import reverse
from django.views.generic import ListView
from django.shortcuts import render, get_object_or_404
from django.core.mail import send_mail

from .models import Post, Comment
from .forms import EmailPostForm, CommentForm
from taggit.models import Tag


def post_list(request, tag_slug=None):
    object_list = Post.published.all()
    tag = None
    if tag_slug:
        tag = get_object_or_404(Tag, slug=tag_slug)
        object_list = object_list.filter(tags__in=[tag])

    paginator = Paginator(object_list, 3)  # 3 posts in each page
    page = request.GET.get('page')
    try:
        posts = paginator.page(page)
    except PageNotAnInteger:
        # If page is not an integer deliver the first page
        posts = paginator.page(1)
    except EmptyPage:
        # If page is out of range deliver last page of results
        posts = paginator.page(paginator.num_pages)
    return render(request, 'blog/post/list.html', {'page': page,
                                                   'posts': posts,
                                                   'tag': tag})


class PostListView(ListView):
    # queryset = Post.published.all() is the same as model = Post
    queryset = Post.published.all()
    context_object_name = 'posts'
    paginate_by = 3
    template_name = 'blog/post/list.html'


def post_detail(request, year, month, day, slug):
    """Only works with 'published' articles.
       In Post model in models.py 'unique_for_date' param was added in the 'slug' field-
       - this ensures that there will be only one post with a slug for a given date.
       Raise Error [404 - Not Found] if no object is found.
    """
    post = get_object_or_404(Post, slug=slug,
                             status='published',
                             publish__year=year,
                             publish__month=month,
                             publish__day=day, )

    # Old comments
    comments = post.comments.filter(active=True)

    new_comment = None

    if request.method == 'POST':
        # A comment was posted
        comment_form = CommentForm(data=request.POST)
        if comment_form.is_valid():
            # Create Comment object but don't save to database yet
            new_comment = comment_form.save(commit=False)
            # Assign the current post to the comment
            new_comment.post = post
            # Save the comment to the database
            new_comment.save()
            return HttpResponseRedirect(reverse('blog:post_detail', args=(year, month, day, slug)))
    else:
        comment_form = CommentForm()

    context = {'post': post, 'comments': comments, 'new_comment': new_comment, 'comment_form': comment_form}
    return render(request, 'blog/post/detail.html', context)

# HttpResponseRedirect(reverse('blog:post_detail', args=(post.publish__year, post.publish__month, post.publish__day,
# post.slug)))


def post_share(request, post_id):
    # Retrieve post by id
    post = get_object_or_404(Post, id=post_id, status='published')
    sent = False

    if request.method == "POST":
        # Form was submitted
        form = EmailPostForm(request.POST)
        if form.is_valid():
            # Form fields passed the validation
            cd = form.cleaned_data
            # ... send email
            post_url = request.build_absolute_uri(
                post.get_absolute_url())
            subject = f"{cd['name']} recommends you read " \
                      f"{post.title}"
            message = f"Read {post.title} at {post_url}\n\n" \
                      f"{cd['name']}\'s comments: {cd['comments']}"
            send_mail(subject, message, 'zokirovrustam202@gmail.com', [cd['to']], fail_silently=False,)
            sent = True
    else:
        form = EmailPostForm()
    return render(request, 'blog/post/share.html', {'post': post, 'form': form, 'sent': sent})
