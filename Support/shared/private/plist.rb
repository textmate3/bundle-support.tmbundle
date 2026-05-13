$LOAD_PATH << "#{ENV['TM_SUPPORT_PATH']}/private/vendor/CFPropertyList/lib"

# Steer CFPropertyList past libxml-ruby (hangs on Ruby 4.0 / libxml-ruby 2.9.0).
# CFPropertyList's auto-detect order is libxml-ruby → nokogiri → REXML; poisoning
# $LOADED_FEATURES makes the inner `require 'libxml'` return false silently, then
# the LibXML:: constant references NameError out and the outer rescue moves on.
require 'rubygems'
$LOADED_FEATURES.concat(Gem.find_files('libxml.rb'))
$LOADED_FEATURES.concat(Gem.find_files('libxml/libxml.rb'))

require 'cfpropertylist'

module Plist
  module_function

  def load(input)
    raw = read_input(input)
    CFPropertyList.native_types(CFPropertyList::List.new(data: raw).value)
  end

  def dump(obj, format: :xml)
    cf_format = { xml: CFPropertyList::List::FORMAT_XML,
                  binary: CFPropertyList::List::FORMAT_BINARY,
                  plain: CFPropertyList::List::FORMAT_PLAIN }.fetch(format)
    plist = CFPropertyList::List.new
    plist.value = CFPropertyList.guess(obj)
    plist.to_str(cf_format)
  end

  def read_input(input)
    return input.read              if input.respond_to?(:read)
    return File.binread(input)     if input.is_a?(String) && !input.include?("\0") && File.exist?(input)
    input
  end

  class << self
    private :read_input
  end
end

[Array, Enumerator, Hash].each do |cls|
  cls.class_eval do
    def to_plist(options = {})
      options[:plist_format] ||= CFPropertyList::List::FORMAT_XML
      plist = CFPropertyList::List.new
      plist.value = CFPropertyList.guess(self, options)
      plist.to_str(options[:plist_format], options)
    end
  end
end
