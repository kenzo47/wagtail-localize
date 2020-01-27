from unittest.mock import patch

from django.conf import settings
from django.test import TestCase

from wagtail.core.models import Page

from wagtail_localize.models import Language, Region, Locale
from wagtail_localize.test.models import InheritedTestModel, TestModel


def make_test_instance(model=None, **kwargs):
    if model is None:
        model = TestModel

    return model.objects.create(**kwargs)


class TestTranslatableMixin(TestCase):
    def setUp(self):
        language_codes = dict(settings.LANGUAGES).keys()

        for language_code in language_codes:
            Language.objects.update_or_create(
                code=language_code, defaults={"is_active": True}
            )

        # create the locales
        self.locale = Locale.objects.get(region__slug="default", language__code="en")
        self.another_locale = Locale.objects.get(
            region__slug="default", language__code="fr"
        )

        # add the main model
        self.main_instance = make_test_instance(
            locale=self.locale, title="Main Model", test_charfield="Some text"
        )

        # add a translated model
        self.translated_model = make_test_instance(
            locale=self.another_locale,
            translation_key=self.main_instance.translation_key,
            title="Translated Model",
        )

        # add a random model that shouldn't show up anywhere
        make_test_instance()

    def test_get_translations_inclusive_false(self):
        self.assertSequenceEqual(
            list(self.main_instance.get_translations()), [self.translated_model]
        )

    def test_get_translations_inclusive_true(self):
        self.assertEqual(
            list(self.main_instance.get_translations(inclusive=True)),
            [self.main_instance, self.translated_model],
        )

    def test_get_translation(self):
        self.assertEqual(
            self.main_instance.get_translation(self.locale), self.main_instance
        )

    def test_get_translation_or_none_return_translation(self):
        with patch.object(
            self.main_instance, "get_translation"
        ) as mock_get_translation:
            mock_get_translation.return_value = self.translated_model
            self.assertEqual(
                self.main_instance.get_translation_or_none(self.another_locale),
                self.translated_model,
            )

    def test_get_translation_or_none_return_none(self):
        self.translated_model.delete()
        with patch.object(
            self.main_instance, "get_translation"
        ) as mock_get_translation:
            mock_get_translation.side_effect = self.main_instance.DoesNotExist
            self.assertEqual(
                self.main_instance.get_translation_or_none(self.another_locale), None
            )

    def test_has_translation_when_exists(self):
        self.assertTrue(self.main_instance.has_translation(self.locale))

    def test_has_translation_when_none_exists(self):
        self.translated_model.delete()
        self.assertFalse(self.main_instance.has_translation(self.another_locale))

    def test_copy_for_translation(self):
        self.translated_model.delete()
        copy = self.main_instance.copy_for_translation(locale=self.another_locale)

        self.assertNotEqual(copy, self.main_instance)
        self.assertEqual(copy.translation_key, self.main_instance.translation_key)
        self.assertEqual(copy.locale, self.another_locale)
        self.assertEqual("Main Model", copy.title)
        self.assertEqual("Some text", copy.test_charfield)

    def test_get_translation_model(self):
        self.assertEqual(self.main_instance.get_translation_model(), TestModel)

        # test with a model that inherits from `TestModel`
        inherited_model = make_test_instance(model=InheritedTestModel)
        self.assertEqual(inherited_model.get_translation_model(), TestModel)

    def test_get_translatable_fields(self):
        field_names = ("test_charfield", "test_textfield", "test_emailfield")
        fields = TestModel.get_translatable_fields()
        self.assertEqual(len(fields), 3)
        for field in fields:
            self.assertIn(field.field_name, field_names)
