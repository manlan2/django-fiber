from django.conf import settings
from django.contrib import admin
from django.contrib.admin.util import model_ngettext
from django.utils.translation import ugettext_lazy as _

from mptt.admin import MPTTModelAdmin

from . import admin_forms as forms
from . import fiber_admin
from .app_settings import TEMPLATE_CHOICES, CONTENT_TEMPLATE_CHOICES
from .editor import get_editor_field_name
from .models import Page, ContentItem, PageContentItem, Image, File
from .utils.class_loader import load_class
from .app_settings import PERMISSION_CLASS


class FileAdmin(admin.ModelAdmin):
    list_display = ('title', '__unicode__')
    date_hierarchy = 'updated'
    search_fields = ('title', )
    actions = ['really_delete_selected']

    def get_actions(self, request):
        actions = super(FileAdmin, self).get_actions(request)
        del actions['delete_selected']  # the original delete selected action doesn't remove associated files, because .delete() is never called
        return actions

    def really_delete_selected(self, request, queryset):
        for obj in queryset:
            obj.delete()

        n = queryset.count()
        self.message_user(request, _("Successfully deleted %(count)d %(items)s.") % {
            "count": n, "items": model_ngettext(self.opts, n)
        })

    really_delete_selected.short_description = _('Delete selected files')


class ImageAdmin(admin.ModelAdmin):
    list_display = ('title', '__unicode__')
    date_hierarchy = 'updated'
    search_fields = ('title', )
    actions = ['really_delete_selected']

    def get_actions(self, request):
        actions = super(ImageAdmin, self).get_actions(request)
        del actions['delete_selected']  # the original delete selected action doesn't remove associated files, because .delete() is never called
        return actions

    def really_delete_selected(self, request, queryset):
        for obj in queryset:
            obj.delete()

        n = queryset.count()
        self.message_user(request, _("Successfully deleted %(count)d %(items)s.") % {
            "count": n, "items": model_ngettext(self.opts, n)
        })

    really_delete_selected.short_description = _('Delete selected images')


class ContentItemAdmin(admin.ModelAdmin):
    list_display = ('__unicode__',)
    form = forms.ContentItemAdminForm
    fieldsets = (
        (None, {'fields': ('name', get_editor_field_name('content_html'),)}),
        (_('Advanced options'), {'classes': ('collapse',), 'fields': ('template_name', 'protected',)}),
        (_('Metadata'), {'classes': ('collapse',), 'fields': ('metadata',)}),
    )
    date_hierarchy = 'updated'
    search_fields = ('name', get_editor_field_name('content_html'))


class PageContentItemInline(admin.TabularInline):
    model = PageContentItem
    extra = 1


class PageAdmin(MPTTModelAdmin):

    form = forms.PageForm
    fieldsets = (
        (None, {'fields': ('parent', 'title', 'url', 'redirect_page', 'template_name')}),
        (_('Advanced options'), {'classes': ('collapse',), 'fields': ('mark_current_regexes', 'show_in_menu', 'is_public', 'protected',)}),
        (_('Metadata'), {'classes': ('collapse',), 'fields': ('metadata',)}),
    )

    inlines = (PageContentItemInline,)
    list_display = ('title', 'view_on_site', 'url', 'redirect_page', 'get_absolute_url', 'action_links')
    list_per_page = 1000
    search_fields = ('title', 'url', 'redirect_page__title')

    def view_on_site(self, page):
        view_on_site = ''

        absolute_url = page.get_absolute_url()
        if absolute_url:
            view_on_site += u'<a href="%s" title="%s" target="_blank"><img src="%sfiber/admin/images/world.gif" width="16" height="16" alt="%s" /></a>' % \
                       (absolute_url, _('View on site'), settings.STATIC_URL, _('View on site'))

        return view_on_site

    view_on_site.short_description = ''
    view_on_site.allow_tags = True

    def action_links(self, page):
        actions = ''

        # first child cannot be moved up, last child cannot be moved down
        if not page.is_first_child():
            actions += u'<a href="%s/move_up" title="%s"><img src="%sfiber/admin/images/arrow_up.gif" width="16" height="16" alt="%s" /></a> ' % (page.pk, _('Move up'), settings.STATIC_URL, _('Move up'))
        else:
            actions += u'<img src="%sfiber/admin/images/blank.gif" width="16" height="16" alt="" /> ' % (settings.STATIC_URL,)

        if not page.is_last_child():
            actions += u'<a href="%s/move_down" title="%s"><img src="%sfiber/admin/images/arrow_down.gif" width="16" height="16" alt="%s" /></a> ' % (page.pk, _('Move down'), settings.STATIC_URL, _('Move down'))
        else:
            actions += u'<img src="%sfiber/admin/images/blank.gif" width="16" height="16" alt="" /> ' % (settings.STATIC_URL,)

        # add subpage
        actions += u'<a href="add/?%s=%s" title="%s"><img src="%sfiber/admin/images/page_new.gif" width="16" height="16" alt="%s" /></a> ' % \
                   (self.model._mptt_meta.parent_attr, page.pk, _('Add sub page'), settings.STATIC_URL, _('Add sub page'))

        return u'<span class="nobr">%s</span>' % (actions,)

    action_links.short_description = _('Actions')
    action_links.allow_tags = True


class FiberAdminContentItemAdmin(fiber_admin.ModelAdmin):
    list_display = ('__unicode__',)
    form = forms.ContentItemAdminForm

    def __init__(self, *args, **kwargs):
        super(FiberAdminContentItemAdmin, self).__init__(*args, **kwargs)

        # remove content template choices if there are no choices
        if len(CONTENT_TEMPLATE_CHOICES) == 0:
            self.fieldsets = (
                (None, {'classes': ('hide-label',), 'fields': (get_editor_field_name('content_html'), )}),
            )
        else:
            self.fieldsets = (
                (None, {'classes': ('hide-label',), 'fields': (get_editor_field_name('content_html'), 'template_name', )}),
            )

    def save_model(self, request, obj, form, change):
        # workaround because not all ajax calls go through the api yet
        super(FiberAdminContentItemAdmin, self).save_model(request, obj, form, change)
        load_class(PERMISSION_CLASS).object_created(request.user, obj)


class FiberAdminPageAdmin(fiber_admin.MPTTModelAdmin):

    form = forms.PageForm

    def __init__(self, *args, **kwargs):
        super(FiberAdminPageAdmin, self).__init__(*args, **kwargs)

        # remove template choices if there are no choices
        if len(TEMPLATE_CHOICES) == 0:
            self.fieldsets = (
                (None, {'fields': ('title', 'url', )}),
                (_('Advanced options'), {'fields': ('redirect_page', 'show_in_menu', 'is_public', )}),
            )
        else:
            self.fieldsets = (
                (None, {'fields': ('title', 'url', )}),
                (_('Advanced options'), {'fields': ('template_name', 'redirect_page', 'show_in_menu', 'is_public', )}),
            )

    def save_model(self, request, obj, form, change):
        if 'before_page_id' in request.POST:
            before_page = Page.objects.get(pk=int(request.POST['before_page_id']))
            obj.parent = before_page.parent
            obj.insert_at(before_page, position='left', save=False)
        elif 'below_page_id' in request.POST:
            below_page = Page.objects.get(pk=int(request.POST['below_page_id']))
            obj.parent = below_page
            obj.insert_at(below_page, position='last-child', save=False)

        super(FiberAdminPageAdmin, self).save_model(request, obj, form, change)

        # workaround because not all ajax calls go through the api yet
        load_class(PERMISSION_CLASS).object_created(request.user, obj)

admin.site.register(ContentItem, ContentItemAdmin)
admin.site.register(Image, ImageAdmin)
admin.site.register(File, FileAdmin)
admin.site.register(Page, PageAdmin)

fiber_admin.site.register(ContentItem, FiberAdminContentItemAdmin)
fiber_admin.site.register(Page, FiberAdminPageAdmin)
