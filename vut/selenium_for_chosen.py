from time import sleep

from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains


class Chosen(object):
    """
    For selenium testing of the jquery Chosen widget (v1.1.0  https://harvesthq.github.io/chosen/).
    The Chosen widget is an enhancement of the HTML <select> tag. It works by generating a whole new set of
    HTML elements and then hiding the original select. This means you cannot use the standard selenium functions
    for select widgets.
    The code below works around these problems.
    """

    def __init__(self, webdriver, select_id, nav_bar_height=50):
        """
        :param webdriver: the driver you get from something like this: webdriver.Firefox()
        :param select_id: the ID of your original select element e.g. <select id="select_id"></select>
        :return:
        """
        self.nav_bar_height = nav_bar_height
        self.webdriver = webdriver
        chosen_id = (select_id + '_chosen').replace('-', '_')
        self.chosen = webdriver.find_element_by_id(chosen_id)
        self.chosen.input = self.chosen.find_element_by_css_selector('.chosen-single')
        self.chosen_drop = self.chosen.find_element_by_css_selector('.chosen-drop')

    def move_from_nav_bar(self, element, max_y=1000000):
        """Make sure element is not under nav bar."""
        if element.location_once_scrolled_into_view['y'] < self.nav_bar_height + 5 or \
                element.location_once_scrolled_into_view['y'] > max_y:
            y = element.location['y'] - 100
            self.webdriver.execute_script("window.scrollTo(0, {})".format(y))
            sleep(1)

    def open_select(self):
        """
        The drop down is "hidden" by setting its left position to -9999px. Its showing when left is 0px.
        """
        # Make sure select is not under nav bar
        self.move_from_nav_bar(self.chosen, max_y=200)

        if self.chosen_drop.value_of_css_property('left') != '0px':
            self.chosen.input.click()
            sleep(0.5)

    def close_select(self):
        """
        The drop down is "hidden" by setting its left position to -9999px. Its showing when left is 0px.
        """
        if self.chosen_drop.value_of_css_property('left') == '0px':
            self.chosen.input.click()
            sleep(0.5)

    def get_options(self, close=True):
        """
        Gets the select options. Note, even though it gets the options when the widget is open, if you close the
        widget and then inspect the text attribute of the results it will be ''. To get the text at the moment the
        widget was open use the method: get_options_text
        :return: a list of selenium elements.
        """
        self.open_select()
        results = self.chosen.find_elements_by_css_selector('.chosen-results li')
        if close:
            self.close_select()
        return results

    def get_options_text(self, close=True):
        """
        Gets the text for each option tag
        :return: a list of selenium elements.
        """
        self.open_select()

        # Making a list locks in the text so it does not change when the select is closed.
        results = [x.text for x in self.chosen.find_elements_by_css_selector('.chosen-results li')]
        if close:
            self.close_select()
        return results

    def get_selected_options(self, close=True):
        """
        :param close: closes the widget when done.
        :return: a list of the text between <option>the text</option> of selected options.
        """
        self.open_select()

        results = []
        for element in self.chosen.find_elements_by_css_selector('ul.chosen-results li.result-selected'):
            self.move_from_nav_bar(element)
            results.append(element.text)

        if close:
            self.close_select()
        return results

    def set_widget(self, select_func):
        """
        The base method for all other methods that set Chosen (see below).
        :param select_func: a function that selects an item from the options list
        :return: None
        """
        results = self.get_options(close=False)
        result = select_func(results)

        if result:
            self.move_from_nav_bar(result)
            ActionChains(self.webdriver).move_to_element(result).perform()
            sleep(1.0)
            result.click()

    def select_by_index(self, index):
        """
        :param index: 0 based index of select option
        :return: None
        """

        def select_func(results):
            for i, result in enumerate(results):
                if i == index:
                    return result
            return None

        self.set_widget(select_func)

    def select_by_value(self, option_value):
        """
        :param option_value: the value param in the html option tag (string)
        :return: None
        """

        def select_func(results):
            for result in results:
                if result.get_attribute('data-option-array-index') == option_value:
                    return result
            return None

        self.set_widget(select_func)

    def select_by_visible_text(self, option_text, exact=False):
        """
        :param option_text: the text contained in the option tag
        :param exact: if not True, we look for the text anywhere in the option text
        :return: None
        """

        def select_func(results):
            for result in results:
                if exact:
                    if result.text == option_text:
                        return result
                else:
                    if result.text.find(option_text) != -1:
                        return result
            return None

        self.set_widget(select_func)

    def select_by_search(self, choice_text):
        """
        Selects an item widget's search function. Not sure why you would use this, but this was the first way
        I figured out how to set Chosen. It works. No reason to delete it.
        :param choice_text: string to be typed into chosen search box
        :return: None
        """
        self.open_select()
        search = self.chosen.find_element_by_css_selector('.chosen-search input')
        search.send_keys(choice_text)
        search.send_keys(Keys.ENTER)

